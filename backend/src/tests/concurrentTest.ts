/**
 * Concurrent Access Test for Queue System
 * Test race conditions with multiple simultaneous requests
 */

import queueService from '../services/queueService';
import redis from 'redis';

const redisClient = redis.createClient({
  socket: {
    host: process.env.REDIS_HOST || 'localhost',
    port: parseInt(process.env.REDIS_PORT || '6379'),
  },
});

redisClient.on('error', (err) => console.log('Redis Client Error', err));
redisClient.connect();

interface TestResult {
  total: number;
  allowed: number;
  queued: number;
  expectedAllowed: number;
  success: boolean;
}

/**
 * Test 1: Simple Concurrent Access
 * Simulate 20 users trying to connect simultaneously
 */
async function testSimpleConcurrent(): Promise<TestResult> {
  console.log('\n🧪 TEST 1: Simple Concurrent Access (20 users)');
  console.log('═══════════════════════════════════════════\n');

  // Reset counters
  await redisClient.del('active_users_count');
  await redisClient.set('active_users_count', '0');

  const numUsers = 20;
  const expectedAllowed = 5; // MAX_CONCURRENT_USERS

  // Create promises for all users
  const promises = Array.from({ length: numUsers }, (_, i) => {
    const sessionId = `session-${i}`;
    const email = `user${i}@example.com`;
    return queueService.checkCanEnter(sessionId, email);
  });

  // Execute all concurrently
  const results = await Promise.all(promises);

  const allowed = results.filter(r => r.canEnter).length;
  const queued = results.filter(r => !r.canEnter).length;

  console.log(`\n📊 Results:`);
  console.log(`   Total Users: ${numUsers}`);
  console.log(`   Allowed In: ${allowed} (Expected: ${expectedAllowed})`);
  console.log(`   Queued: ${queued} (Expected: ${numUsers - expectedAllowed})`);

  const success = allowed === expectedAllowed && queued === numUsers - expectedAllowed;
  console.log(`   Status: ${success ? '✅ PASSED' : '❌ FAILED'}`);

  return { total: numUsers, allowed, queued, expectedAllowed, success };
}

/**
 * Test 2: Sequential Waves with Timeout
 * Simulate users entering and leaving in waves
 */
async function testSequentialWaves(): Promise<TestResult> {
  console.log('\n🧪 TEST 2: Sequential Waves (5 waves of 10 users)');
  console.log('═══════════════════════════════════════════════\n');

  // Reset
  await redisClient.del('active_users_count');
  await redisClient.set('active_users_count', '0');

  let totalAllowed = 0;
  let totalQueued = 0;

  const waveSize = 10;
  const numWaves = 5;

  for (let wave = 1; wave <= numWaves; wave++) {
    console.log(`\n📈 Wave ${wave}:`);

    // Clear queue for new wave
    const oldQueueKeys = await redisClient.keys('queue:*');
    if (oldQueueKeys.length > 0) {
      await Promise.all(oldQueueKeys.map(key => redisClient.del(key)));
    }

    // Create users for this wave
    const promises = Array.from({ length: waveSize }, (_, i) => {
      const sessionId = `wave${wave}-user${i}`;
      const email = `wave${wave}user${i}@example.com`;
      return queueService.checkCanEnter(sessionId, email);
    });

    const results = await Promise.all(promises);
    const allowed = results.filter(r => r.canEnter).length;
    const queued = results.filter(r => !r.canEnter).length;

    totalAllowed += allowed;
    totalQueued += queued;

    console.log(`   Allowed: ${allowed}, Queued: ${queued}`);

    // Wait 1 second before next wave
    await new Promise(r => setTimeout(r, 1000));
  }

  const success = totalAllowed <= 5 * numWaves; // Max 5 at a time
  console.log(`\n📊 Total Results:`);
  console.log(`   Total Allowed: ${totalAllowed}`);
  console.log(`   Total Queued: ${totalQueued}`);
  console.log(`   Status: ${success ? '✅ PASSED' : '❌ FAILED'}`);

  return { total: waveSize * numWaves, allowed: totalAllowed, queued: totalQueued, expectedAllowed: 5, success };
}

/**
 * Test 3: Stress Test
 * High-volume concurrent requests
 */
async function testStressLoad(): Promise<TestResult> {
  console.log('\n🧪 TEST 3: Stress Test (100 concurrent requests)');
  console.log('═════════════════════════════════════════════════\n');

  // Reset
  await redisClient.del('active_users_count');
  await redisClient.set('active_users_count', '0');

  const numUsers = 100;
  const expectedAllowed = 5;

  const startTime = Date.now();

  const promises = Array.from({ length: numUsers }, (_, i) => {
    const sessionId = `stress-session-${i}`;
    const email = `stressuser${i}@example.com`;
    return queueService.checkCanEnter(sessionId, email);
  });

  const results = await Promise.all(promises);
  const duration = Date.now() - startTime;

  const allowed = results.filter(r => r.canEnter).length;
  const queued = results.filter(r => !r.canEnter).length;

  console.log(`\n⏱️  Performance:`);
  console.log(`   Duration: ${duration}ms`);
  console.log(`   Avg per request: ${(duration / numUsers).toFixed(2)}ms`);

  console.log(`\n📊 Results:`);
  console.log(`   Total Users: ${numUsers}`);
  console.log(`   Allowed In: ${allowed} (Expected: ${expectedAllowed})`);
  console.log(`   Queued: ${queued}`);

  const success = allowed === expectedAllowed;
  console.log(`   Status: ${success ? '✅ PASSED' : '❌ FAILED'}`);

  return { total: numUsers, allowed, queued, expectedAllowed, success };
}

/**
 * Test Runner
 */
async function runAllTests() {
  console.log('🚀 STARTING CONCURRENT ACCESS TESTS');
  console.log('═════════════════════════════════════════════\n');

  const results: TestResult[] = [];

  try {
    results.push(await testSimpleConcurrent());
    // Reset between tests
    await new Promise(r => setTimeout(r, 1000));

    results.push(await testSequentialWaves());
    // Reset between tests
    await new Promise(r => setTimeout(r, 1000));

    results.push(await testStressLoad());
  } catch (error) {
    console.error('❌ Test error:', error);
  }

  // Summary
  console.log('\n\n📋 TEST SUMMARY');
  console.log('═════════════════════════════════════════════');
  const passedTests = results.filter(r => r.success).length;
  const totalTests = results.length;

  console.log(`Passed: ${passedTests}/${totalTests}`);
  if (passedTests === totalTests) {
    console.log('✅ All tests passed!');
  } else {
    console.log(`❌ ${totalTests - passedTests} test(s) failed`);
  }

  // Cleanup
  await redisClient.quit();
  process.exit(passedTests === totalTests ? 0 : 1);
}

// Run tests
runAllTests().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
