module.exports = {
  testEnvironment: 'node',
  testTimeout: 30000, // 30 seconds for extension tests with browser automation
  verbose: true,
  collectCoverageFrom: [
    'extension/**/*.js',
    '!extension/lib/**', // Exclude third-party libraries
    '!**/node_modules/**',
  ],
  testMatch: [
    '**/tests/**/*.test.js',
  ],
};
