module.exports = {
  testEnvironment: 'node',
  testTimeout: 60000, // 60 seconds for extension tests with browser automation (increased for slow content script injection)
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
