# 🧪 Concurrent Access Testing Guide

## Overview
This document explains how to test the queue system's handling of concurrent user access.

---

## 🚀 Quick Start

### Prerequisites
- Backend server running: `npm start` (or `npm run dev`)
- Redis running locally on port 6379

### Test Options

#### Option 1: Unit/Integration Tests (Redis Direct)
Tests the queue service directly without HTTP overhead.

```bash
# Navigate to backend
cd backend

# Run concurrent access test
npm run test:concurrent
```

**What it tests:**
- Race condition prevention with atomic INCR
- Correct slot allocation (max 5 users)
- Queue position calculation
- Multiple waves of users

**Expected Output:**
```
🧪 TEST 1: Simple Concurrent Access (20 users)
═══════════════════════════════════════════

📊 Results:
   Total Users: 20
   Allowed In: 5 (Expected: 5)
   Queued: 15 (Expected: 15)
   Status: ✅ PASSED
```

---

#### Option 2: HTTP Load Test
Tests the actual API endpoints with real HTTP requests.

```bash
# Terminal 1: Start backend
npm start

# Terminal 2: Run load test
npm run test:load
```

**What it tests:**
- Real HTTP request handling
- Network latency impact
- API response times
- Authentication flow under load

**Expected Output:**
```
🚀 Starting Load Test
   URL: http://localhost:3001/api/auth/login
   Method: POST
   Total Requests: 20
   Concurrent: 5

✓ Completed 20/20 requests

📊 Load Test Results
═══════════════════════════════════════════
Total Requests: 20
Successful (2xx): 20
Failed (5xx): 0

⏱️  Timing (ms):
   Average: 5.32
   Min: 2
   Max: 18

📈 Queue Stats:
   Allowed In: 5
   Queued: 15
   Accuracy: ✅ PASS
═══════════════════════════════════════════
```

---

## 🔧 Advanced Testing Methods

### Option 3: Apache Bench (CLI Tool)
Simple command-line load testing.

```bash
# Install Apache Bench (if not already)
# Windows: choco install apache-httpd
# Mac: brew install httpd
# Linux: sudo apt-get install apache2-utils

# Run test
ab -n 50 -c 10 -p Body.json -H "Content-Type: application/json" \
   http://localhost:3001/api/auth/login
```

**Parameters:**
- `-n 50`: Total number of requests
- `-c 10`: Concurrency (simultaneous requests)
- `-p Body.json`: POST data file

**Sample Body.json:**
```json
{
  "email": "testuser@example.com",
  "password": "password123",
  "sessionId": "test-session-12345"
}
```

**Output example:**
```
Concurrency Level:      10
Time taken for tests:   1.234 seconds
Requests per second:    40.52 [#/sec]
Time per request:       246.80 [ms]
Failed requests:        0
```

---

### Option 4: cURL (Multiple Sequential Requests)
Test manually with individual requests.

```bash
# Test 1: First user (should be allowed in)
curl -X POST http://localhost:3001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user1@example.com",
    "password": "password123",
    "sessionId": "session-1"
  }'

# Response should have: "canEnter": true

# Test 2: 5th user (should be allowed in)
curl -X POST http://localhost:3001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user5@example.com",
    "password": "password123",
    "sessionId": "session-5"
  }'

# Response should have: "canEnter": true

# Test 3: 6th user (should be queued)
curl -X POST http://localhost:3001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user6@example.com",
    "password": "password123",
    "sessionId": "session-6"
  }'

# Response should have: "canEnter": false, "position": 1
```

---

### Option 5: Autocannon (Professional Load Testing)
Install and use autocannon for detailed performance metrics.

```bash
# Install globally
npm install -g autocannon

# Run test
autocannon -c 10 -d 30 -p 5 \
  --method POST \
  --body '{"email":"test@example.com","password":"pass","sessionId":"session"}' \
  http://localhost:3001/api/auth/login
```

**Parameters:**
- `-c 10`: 10 concurrent connections
- `-d 30`: Duration 30 seconds
- `-p 5`: 5 pipelined requests

---

### Option 6: Custom Node.js Script
Create your own test script:

```typescript
// test-custom.ts
import http from 'http';

const numRequests = 100;
const concurrent = 15;

let completed = 0;
let allowed = 0;
let queued = 0;

const sendRequest = (index: number) => {
  const payload = JSON.stringify({
    email: `user${index}@example.com`,
    password: 'password123',
    sessionId: `session-${index}`
  });

  const options = {
    hostname: 'localhost',
    port: 3001,
    path: '/api/auth/login',
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(payload)
    }
  };

  const req = http.request(options, (res) => {
    let data = '';
    res.on('data', chunk => data += chunk);
    res.on('end', () => {
      const response = JSON.parse(data);
      if (response.canEnter) allowed++;
      else queued++;
      completed++;
      
      console.log(`✓ Request ${index}: ${response.canEnter ? 'ALLOWED' : 'QUEUED'}`);
    });
  });

  req.write(payload);
  req.end();
};

// Run test
for (let i = 0; i < numRequests; i++) {
  sendRequest(i);
  if (i % concurrent === concurrent - 1) {
    setTimeout(() => {}, 100);
  }
}

setTimeout(() => {
  console.log(`\nResults: Allowed=${allowed}, Queued=${queued}`);
}, 5000);
```

Run with: `npx ts-node test-custom.ts`

---

## 📊 Test Scenarios

### Scenario 1: Basic Concurrency
**Goal:** Verify exactly 5 users can be active
- Send 10 concurrent requests
- Expect: 5 allowed, 5 queued

### Scenario 2: Queue Promotion  
**Goal:** Verify first-in-first-out queue behavior
1. Fill all 5 slots
2. Send more requests (they queue)
3. One user logs out
4. Verify first queued user is promoted

### Scenario 3: High Load Stress
**Goal:** Verify system stability under heavy load
- Send 100+ concurrent requests
- Check no race conditions
- Verify counter accuracy

### Scenario 4: Timeout Handling
**Goal:** Verify expired queue entries are cleaned
- Queue users
- Wait for QUEUE_TIMEOUT (60 seconds)
- Verify entries are removed

---

## ✅ Success Criteria

```
✅ PASS if:
  - Exactly 5 users allowed in
  - Rest are queued
  - No race conditions
  - Average response time < 50ms
  - No memory leaks
  - Counter is accurate

❌ FAIL if:
  - >5 users allowed in
  - Race conditions detected
  - Response errors
  - Memory growing continuously
```

---

## 🔍 Metrics to Monitor

While testing, watch these metrics:

```bash
# Redis Monitor (real-time commands)
redis-cli MONITOR

# Redis Info (memory, events, etc.)
redis-cli INFO stats
redis-cli INFO memory

# Check active users count
redis-cli GET active_users_count

# List all queue entries
redis-cli KEYS "queue:*"
redis-cli KEYS "active_user:*"
```

---

## 📝 Performance Expectations

```
Metric                  Expected Value
─────────────────────────────────────
Response Time           5-20ms (network dependent)
Throughput              200-500 req/sec
Max Concurrent Users    5 (hardcoded limit)
Queue Timeout           60 seconds
Session Timeout         30 minutes
```

---

## 🐛 Debugging Tips

### Check Redis Keys
```bash
redis-cli KEYS "*"
```

### Monitor Live Commands
```bash
redis-cli MONITOR
```

### Check Counter Value
```bash
redis-cli GET active_users_count
```

### Clear All Data (Testing Only)
```bash
redis-cli FLUSHDB
# OR
redis-cli FLUSHALL
```

### View Queue Status
```bash
# Get all queue users
redis-cli KEYS "queue:*" | xargs redis-cli MGET

# Get all active users  
redis-cli KEYS "active_user:*" | xargs redis-cli MGET
```

---

## 🚀 CI/CD Integration

Add to your CI pipeline:

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-node@v2
        with:
          node-version: '18'
      
      - run: cd backend && npm install
      - run: npm run test:concurrent
      - run: npm run test:load
```

---

## 📚 References

- [Redis Documentation](https://redis.io/docs/)
- [INCR Command](https://redis.io/commands/incr/)
- [Apache Bench Guide](https://httpd.apache.org/docs/current/programs/ab.html)
- [Autocannon](https://github.com/mcollina/autocannon)
