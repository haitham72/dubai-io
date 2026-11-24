import type { ConfigContext, ExpoConfig } from "expo/config";

export default ({ config }: ConfigContext): ExpoConfig => {
  const envUrl = process.env.EXPO_PUBLIC_COMMUNITY_URL || process.env.COMMUNITY_URL;
  return {
    ...config,
    name: config.name ?? "Dubai-io Community",
    slug: config.slug ?? "dubai-io-community",
    extra: {
      ...(config.extra ?? {}),
      communityUrl: envUrl || (config.extra?.communityUrl as string | undefined) || "http://localhost:3060",
    },
  };
};
