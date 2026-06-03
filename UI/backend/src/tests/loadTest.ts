/**
 * HTTP Load Test - Simulate concurrent login requests
 * Run with: npx ts-node src/tests/loadTest.ts
 */

import http from 'http';
import redis from 'redis';
import { getNumberEnv, getRequiredEnv } from '../config/env';

interface LoadTestOptions {
  url: string;
  method: string;
  numRequests: number;
  concurrent: number;
}

interface LoadTestResult {
  totalRequests: number;
  successCount: number;
  failureCount: number;
  averageTime: number;
  minTime: number;
  maxTime: number;
  allowedIn: number;
  queued: number;
}

class LoadTester {
  private results: { statusCode: number; time: number; canEnter?: boolean }[] = [];

  async resetRedisState(): Promise<void> {
    const redisClient = redis.createClient({
      socket: {
        host: getRequiredEnv('REDIS_HOST'),
        port: getNumberEnv('REDIS_PORT'),
      },
    });

    redisClient.on('error', (error) => {
      console.error('Redis Client Error:', error);
    });

    await redisClient.connect();

    try {
      await redisClient.del('active_users_count');

      const queueKeys = await redisClient.keys('queue:*');
      if (queueKeys.length > 0) {
        await Promise.all(queueKeys.map((key) => redisClient.del(key)));
      }

      const activeKeys = await redisClient.keys('active_user:*');
      if (activeKeys.length > 0) {
        await Promise.all(activeKeys.map((key) => redisClient.del(key)));
      }
    } finally {
      await redisClient.quit();
    }
  }

  async runLoadTest(options: LoadTestOptions): Promise<LoadTestResult> {
    const { url, method, numRequests, concurrent } = options;
    const urlObj = new URL(url);

    this.results = [];

    console.log(`\n🚀 Starting Load Test`);
    console.log(`   URL: ${url}`);
    console.log(`   Method: ${method}`);
    console.log(`   Total Requests: ${numRequests}`);
    console.log(`   Concurrent: ${concurrent}\n`);

    const startTime = Date.now();
    let currentIndex = 0;
    let activeRequests = 0;

    return new Promise((resolve) => {
      const sendRequest = () => {
        while (currentIndex < numRequests && activeRequests < concurrent) {
          activeRequests++;
          const requestIndex = currentIndex++;
          this.makeRequest(urlObj, method, requestIndex).finally(() => {
            activeRequests--;
            if (currentIndex < numRequests) {
              sendRequest();
            } else if (activeRequests === 0) {
              finishTest();
            }
          });
        }
      };

      const finishTest = () => {
        const totalTime = Date.now() - startTime;
        const result = this.calculateResults(totalTime);
        
        console.log('\n📊 Load Test Results');
        console.log('═══════════════════════════════════════════');
        console.log(`Total Requests: ${result.totalRequests}`);
        console.log(`Successful (2xx): ${result.successCount}`);
        console.log(`Failed (5xx): ${result.failureCount}`);
        console.log(`\n⏱️  Timing (ms):`);
        console.log(`   Average: ${result.averageTime.toFixed(2)}`);
        console.log(`   Min: ${result.minTime}`);
        console.log(`   Max: ${result.maxTime}`);
        console.log(`\n📈 Queue Stats:`);
        console.log(`   Allowed In: ${result.allowedIn}`);
        console.log(`   Queued: ${result.queued}`);
        console.log(`   Accuracy: ${result.allowedIn === 5 ? '✅ PASS' : '❌ FAIL'}`);
        console.log('═══════════════════════════════════════════\n');

        resolve(result);
      };

      sendRequest();
    });
  }

  private makeRequest(
    urlObj: URL,
    method: string,
    index: number
  ): Promise<void> {
    return new Promise((resolve) => {
      const startTime = Date.now();
      const payload = JSON.stringify({
        username: `loadtest${index}`,
        password: 'password123',
        sessionId: `session-${index}-${Date.now()}`
      });

      const options = {
        hostname: urlObj.hostname,
        port: urlObj.port || 3001,
        path: urlObj.pathname,
        method: method,
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(payload)
        }
      };

      const req = http.request(options, (res) => {
        let data = '';
        res.on('data', (chunk) => (data += chunk));
        res.on('end', () => {
          const time = Date.now() - startTime;
          let canEnter = false;
          try {
            const body = JSON.parse(data || '{}');
            canEnter = !!body.canEnter;
          } catch (e) {
            // ignore parse errors
          }

          this.results.push({ statusCode: res.statusCode || 0, time, canEnter });

          if ((index + 1) % 10 === 0) {
            process.stdout.write(`\r✓ Completed ${index + 1}/${this.results.length} requests`);
          }

          resolve();
        });
      });

      req.on('error', (error) => {
        console.error(`\n❌ Request ${index} failed:`, error.message);
        this.results.push({ statusCode: 0, time: Date.now() - startTime, canEnter: false });
        resolve();
      });

      req.write(payload);
      req.end();
    });
  }

  private calculateResults(_totalTime: number): LoadTestResult {
    const times = this.results.map(r => r.time);
    const successCount = this.results.filter(r => r.statusCode >= 200 && r.statusCode < 300).length;
    const failureCount = this.results.filter(r => r.statusCode >= 500).length;
    const allowedIn = this.results.filter(r => r.canEnter).length;

    const avg = times.length ? times.reduce((a, b) => a + b, 0) / times.length : 0;
    const min = times.length ? Math.min(...times) : 0;
    const max = times.length ? Math.max(...times) : 0;

    return {
      totalRequests: this.results.length,
      successCount,
      failureCount,
      averageTime: avg,
      minTime: min,
      maxTime: max,
      allowedIn,
      queued: this.results.length - allowedIn
    };
  }
}

function getAuthLoginUrl(): string {
  const explicitUrl = process.env.AUTH_LOGIN_URL;

  if (explicitUrl) {
    return explicitUrl;
  }

  return `${getRequiredEnv('AUTH_API_URL')}/api/auth/login`;
}

/**
 * Main - Run load test
 */
async function main() {
  const tester = new LoadTester();

  await tester.resetRedisState();

  // Test 1: Simple load
  await tester.runLoadTest({
    url: getAuthLoginUrl(),
    method: 'POST',
    numRequests: 20,
    concurrent: 5
  });

  console.log('\n⏳ Waiting 2 seconds before stress test...\n');
  await new Promise(r => setTimeout(r, 2000));

  await tester.resetRedisState();

  // Test 2: Stress test
  await tester.runLoadTest({
    url: getAuthLoginUrl(),
    method: 'POST',
    numRequests: 100,
    concurrent: 20
  });

  process.exit(0);
}

main().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
