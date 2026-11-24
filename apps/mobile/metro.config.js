const path = require("path");
const { getDefaultConfig } = require("expo/metro-config");

const projectRoot = __dirname;
const tokensRoot = path.resolve(projectRoot, "../../packages/design-tokens");
const config = getDefaultConfig(projectRoot);

config.watchFolders = [tokensRoot];
config.resolver.nodeModulesPaths = [path.resolve(projectRoot, "node_modules")];
config.resolver.extraNodeModules = {
  "@dubai-io/design-tokens": tokensRoot,
};

module.exports = config;
