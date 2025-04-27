/** @type {import('prettier').Config} */
module.exports = {
  printWidth: 100,
  tabWidth: 2,
  useTabs: false,
  semi: true,
  singleQuote: true,
  trailingComma: 'es5',
  bracketSpacing: true,
  arrowParens: 'avoid',
  endOfLine: 'lf',
  // Ensure JSON files are properly formatted
  overrides: [
    {
      files: '*.json',
      options: {
        parser: 'json',
        tabWidth: 2
      }
    },
    {
      files: '*.jsonc',
      options: {
        parser: 'json',
        tabWidth: 2
      }
    }
  ]
};
