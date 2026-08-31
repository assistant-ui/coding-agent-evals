const { getDefaultConfig } = require("expo/metro-config");
const { withAui } = require("@assistant-ui/metro");

const config = getDefaultConfig(__dirname);

module.exports = withAui(config);
