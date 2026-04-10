import redis from 'redis';

const redisClient = redis.createClient({
  socket: {
    host: process.env.REDIS_HOST || 'localhost',
    port: parseInt(process.env.REDIS_PORT || '6379'),
  },
});

redisClient.on('error', (err) => console.log('Redis Client Error', err));
redisClient.connect();

const MAX_CONCURRENT_USERS = 5;
const SESSION_TIMEOUT = 30 * 60; // 30 minutes
const QUEUE_TIMEOUT = 60; // 1 minute

// ========== COMMENTED: QueuePosition Interface (Not used) ==========
// interface QueuePosition {
//   sessionId: string;
//   email: string;
//   timestamp: number;
//   position: number;
// }

class QueueService {
  /**
   * Check if user can enter (active users < 5)
   * Using atomic INCR to prevent race conditions
   */
  async checkCanEnter(sessionId: string, email: string): Promise<{ canEnter: boolean; position?: number; waitTime?: number }> {
    try {
      // Step 1: Atomically increment counter
      const newCount = await redisClient.incr('active_users_count');

      if (newCount <= MAX_CONCURRENT_USERS) {
        // User can enter - add to active users
        const key = `active_user:${sessionId}`;
        await redisClient.setEx(key, SESSION_TIMEOUT, JSON.stringify({ email, timestamp: Date.now() }));
        console.log(`✅ User ${email} entered. Active: ${newCount}/${MAX_CONCURRENT_USERS}`);
        return { canEnter: true };
      } else {
        // Exceeded limit - decrement counter and add to queue instead
        await redisClient.decr('active_users_count');
        const queueKey = `queue:${sessionId}`;
        await redisClient.setEx(queueKey, QUEUE_TIMEOUT, JSON.stringify({ email, timestamp: Date.now() }));
        
        // Get queue position
        const queueKeys = await redisClient.keys('queue:*');
        const position = queueKeys.length;
        const waitTime = Math.ceil((position - 1) / 2) * 60; // Estimate: 2 users per minute
        
        console.log(`⏳ User ${email} queued. Position: ${position} (Wait: ~${waitTime}s)`);
        return { canEnter: false, position, waitTime };
      }
    } catch (error) {
      console.error('Error checking queue:', error);
      return { canEnter: false, position: 999, waitTime: 0 };
    }
  }

  /**
   * Add user to active users list (Direct - called from checkCanEnter)
   */
  async addActiveUser(sessionId: string, email: string): Promise<void> {
    try {
      const key = `active_user:${sessionId}`;
      await redisClient.setEx(key, SESSION_TIMEOUT, JSON.stringify({ email, timestamp: Date.now() }));
      console.log(`✅ User added to active: ${email}`);
    } catch (error) {
      console.error('Error adding active user:', error);
    }
  }

  /**
   * Add user to queue (Direct - called from checkCanEnter)
   */
  async addToQueue(sessionId: string, email: string): Promise<number> {
    try {
      const queueKey = `queue:${sessionId}`;
      await redisClient.setEx(queueKey, QUEUE_TIMEOUT, JSON.stringify({ email, timestamp: Date.now() }));
      
      const queueKeys = await redisClient.keys('queue:*');
      const position = queueKeys.length;

      console.log(`⏳ User added to queue: ${email} (Position: ${position})`);
      return position;
    } catch (error) {
      console.error('Error adding to queue:', error);
      return 999;
    }
  }

  /**
   * Remove user from active list
   */
  async removeActiveUser(sessionId: string): Promise<void> {
    try {
      const key = `active_user:${sessionId}`;
      const exists = await redisClient.exists(key);

      if (exists) {
        await redisClient.del(key);

        const currentCount = await redisClient.get('active_users_count');
        const newCount = Math.max(0, parseInt(currentCount || '1') - 1).toString();
        await redisClient.set('active_users_count', newCount);

        console.log(`❌ User removed from active (${newCount}/${MAX_CONCURRENT_USERS})`);

        // Try to move first user from queue to active
        await this.promoteFromQueue();
      }
    } catch (error) {
      console.error('Error removing active user:', error);
    }
  }

  /**
   * Promote first user in queue to active
   */
  async promoteFromQueue(): Promise<void> {
    try {
      const queueKeys = await redisClient.keys('queue:*');
      if (queueKeys.length === 0) return;

      // Get first user in queue
      const firstQueueKey = queueKeys[0];
      const queueData = await redisClient.get(firstQueueKey);

      if (queueData) {
        const { email } = JSON.parse(queueData);
        const sessionId = firstQueueKey.replace('queue:', '');

        // Move to active
        await redisClient.del(firstQueueKey);
        await this.addActiveUser(sessionId, email);

        console.log(`⬆️  Promoted from queue: ${email}`);
      }
    } catch (error) {
      console.error('Error promoting from queue:', error);
    }
  }

  /**
   * Get current stats
   */
  async getStats(): Promise<{ activeUsers: number; queuedUsers: number; canEnter: boolean }> {
    try {
      const activeCount = parseInt(await redisClient.get('active_users_count') || '0');
      const queueKeys = await redisClient.keys('queue:*');
      const queuedCount = queueKeys.length;

      return {
        activeUsers: activeCount,
        queuedUsers: queuedCount,
        canEnter: activeCount < MAX_CONCURRENT_USERS
      };
    } catch (error) {
      console.error('Error getting stats:', error);
      return { activeUsers: 0, queuedUsers: 0, canEnter: true };
    }
  }

  /**
   * Get user position in queue
   */
  async getUserQueuePosition(sessionId: string): Promise<number | null> {
    try {
      const queueKey = `queue:${sessionId}`;
      const exists = await redisClient.exists(queueKey);
      
      if (!exists) return null;

      const queueKeys = await redisClient.keys('queue:*');
      const position = queueKeys.indexOf(queueKey) + 1;
      return position;
    } catch (error) {
      console.error('Error getting queue position:', error);
      return null;
    }
  }

  /**
   * Check if user is active
   */
  async isUserActive(sessionId: string): Promise<boolean> {
    try {
      const key = `active_user:${sessionId}`;
      return await redisClient.exists(key) > 0;
    } catch (error) {
      console.error('Error checking active status:', error);
      return false;
    }
  }
}

export default new QueueService();
