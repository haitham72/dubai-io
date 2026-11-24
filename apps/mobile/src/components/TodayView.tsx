import React, { useEffect, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, useWindowDimensions, View } from "react-native";
import { cardViewportWidth, colors, noShadow, radii, spacing, typography } from "@dubai-io/design-tokens";
import { getTodayFeed, type TodayFeedResponse } from "../lib/api";
import { useApiSettingsOptional } from "../lib/api-settings";
import { useAuthOptional } from "../lib/auth";
import { karimToday, todayRails } from "../lib/fixtures";
import { DemoPill } from "./DemoPill";
import { TodayCarouselCard } from "./TodayCarouselCard";

export function TodayView({
  onOpenSettings,
  apiBaseUrl: propApiBaseUrl,
  sessionToken: propSessionToken,
  displayName: propDisplayName,
  demo: propDemo,
  fetchImpl,
}: {
  onOpenSettings: () => void;
  apiBaseUrl?: string;
  sessionToken?: string | null;
  displayName?: string | null;
  demo?: boolean;
  fetchImpl?: typeof fetch;
}) {
  const { width } = useWindowDimensions();
  const cardWidth = Math.round(width * cardViewportWidth);
  const auth = useAuthOptional();
  const apiSettings = useApiSettingsOptional();

  const demo = propDemo ?? auth?.demoMode ?? false;
  const apiBaseUrl = propApiBaseUrl ?? apiSettings?.apiBaseUrl ?? "";
  const sessionToken = propSessionToken !== undefined ? propSessionToken : auth?.session?.sessionToken ?? null;
  const displayName = propDisplayName !== undefined ? propDisplayName : auth?.session?.displayName ?? null;

  const [playbackNote, setPlaybackNote] = useState<string | null>(null);
  const [feed, setFeed] = useState<TodayFeedResponse | null>(null);

  useEffect(() => {
    if (demo) return;
    let cancelled = false;
    getTodayFeed(apiBaseUrl, { sessionToken }, { fetchImpl }).then((res) => {
      if (!cancelled) setFeed(res);
    });
    return () => {
      cancelled = true;
    };
  }, [demo, apiBaseUrl, sessionToken, fetchImpl]);

  const greetingText = demo
    ? karimToday.greeting
    : displayName
      ? `Good morning, ${displayName}`
      : "Good morning";

  return (
    <ScrollView contentContainerStyle={styles.page} testID="today-screen">
      <View style={styles.header}>
        <Text style={styles.brand}>Dubai-io</Text>
        <View style={styles.headerActions}>
          <View style={styles.vip}>
            <Text style={styles.vipText}>{demo ? "Demo" : "Quest"}</Text>
          </View>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Connect and settings"
            onPress={onOpenSettings}
            testID="open-settings"
          >
            <Text style={styles.gear}>⚙</Text>
          </Pressable>
        </View>
      </View>

      <Text style={styles.greeting}>{greetingText}</Text>
      {demo ? <Text style={styles.place}>{karimToday.placeLine}</Text> : null}

      {demo ? (
        <>
          <View style={styles.hero} testID="weekly-recap">
            <DemoPill />
            <Text style={styles.heroTitle}>{karimToday.recapTitle}</Text>
            <Text style={styles.heroBody}>{karimToday.recapBody}</Text>
            <Pressable
              accessibilityRole="button"
              onPress={() => setPlaybackNote("Playback is not connected. This weekly recap is demo data.")}
              style={styles.watch}
              testID="watch-recap"
            >
              <Text style={styles.watchText}>Watch Recap</Text>
            </Pressable>
            {playbackNote ? <Text style={styles.note}>{playbackNote}</Text> : null}
          </View>

          {todayRails.map((rail) => (
            <View key={rail.id} style={styles.rail}>
              <Text style={styles.railTitle}>{rail.title}</Text>
              <ScrollView
                horizontal
                decelerationRate="fast"
                showsHorizontalScrollIndicator={false}
                snapToInterval={cardWidth + spacing.md}
                contentContainerStyle={styles.railRow}
              >
                {rail.cards.map((card) => (
                  <TodayCarouselCard key={card.id} card={card} width={cardWidth} />
                ))}
              </ScrollView>
            </View>
          ))}
        </>
      ) : feed && feed.status === "ok" && feed.cards.length > 0 ? (
        <View style={styles.rail} testID="today-live-feed">
          <Text style={styles.railTitle}>For you today</Text>
          {feed.asOf ? <Text style={styles.note}>Updated {feed.asOf}</Text> : null}
          <ScrollView
            horizontal
            decelerationRate="fast"
            showsHorizontalScrollIndicator={false}
            snapToInterval={cardWidth + spacing.md}
            contentContainerStyle={styles.railRow}
          >
            {feed.cards.map((card) => (
              <TodayCarouselCard key={card.id} card={card} width={cardWidth} />
            ))}
          </ScrollView>
        </View>
      ) : (
        <View style={styles.hero} testID="today-feed-not-ready">
          <Text style={styles.heroTitle}>Feed not ready</Text>
          <Text style={styles.heroBody}>
            {feed?.emptyReason || "Your personalized Today feed will appear here once your memory and feed generator are ready."}
          </Text>
          <Pressable accessibilityRole="button" onPress={onOpenSettings} style={styles.watch} testID="today-open-connect">
            <Text style={styles.watchText}>Open Connect</Text>
          </Pressable>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: {
    ...noShadow,
    backgroundColor: colors.canvas,
    gap: spacing.lg,
    padding: spacing.lg,
    paddingBottom: 120,
  },
  header: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
  },
  brand: {
    color: colors.ink,
    fontFamily: typography.serif,
    fontSize: typography.brand,
  },
  headerActions: {
    alignItems: "center",
    flexDirection: "row",
    gap: spacing.sm,
  },
  vip: {
    ...noShadow,
    backgroundColor: colors.gold.surface,
    borderColor: colors.gold.border,
    borderRadius: radii.pill,
    borderWidth: 1,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
  },
  vipText: {
    color: colors.gold.primary,
    fontSize: typography.caption,
    fontWeight: "700",
  },
  gear: {
    color: colors.ink,
    fontSize: 20,
  },
  greeting: {
    color: colors.ink,
    fontFamily: typography.serif,
    fontSize: typography.display,
  },
  place: {
    color: colors.muted,
    fontSize: typography.body,
    marginTop: -spacing.sm,
  },
  hero: {
    ...noShadow,
    backgroundColor: colors.surface,
    borderColor: colors.gold.border,
    borderRadius: radii.card,
    borderWidth: 1,
    gap: spacing.sm,
    padding: spacing.lg,
  },
  heroTitle: {
    color: colors.ink,
    fontFamily: typography.serif,
    fontSize: typography.title,
  },
  heroBody: {
    color: colors.ink,
    fontSize: typography.body,
    lineHeight: 22,
  },
  watch: {
    ...noShadow,
    alignSelf: "flex-start",
    backgroundColor: colors.card,
    borderColor: colors.border,
    borderRadius: radii.pill,
    borderWidth: 1,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
  },
  watchText: {
    color: colors.ink,
    fontWeight: "600",
  },
  note: {
    color: colors.muted,
    fontSize: typography.caption,
  },
  rail: {
    gap: spacing.sm,
  },
  railTitle: {
    color: colors.ink,
    fontFamily: typography.serif,
    fontSize: typography.title,
  },
  railRow: {
    gap: spacing.md,
    paddingRight: spacing.xl,
  },
});
