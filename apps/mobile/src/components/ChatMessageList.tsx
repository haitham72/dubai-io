import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { colors, noShadow, radii, spacing, typography } from "@dubai-io/design-tokens";
import type { ChatMessage } from "../lib/types";
import { DemoPill } from "./DemoPill";
import { MemoryIngestedBadge } from "./MemoryIngestedBadge";

export function ChatMessageList({ messages }: { messages: ChatMessage[] }) {
  return (
    <View style={styles.list} testID="chat-message-list">
      {messages.map((message) => {
        const mine = message.role === "user";
        return (
          <View key={message.id} style={[styles.row, mine ? styles.rowUser : styles.rowAi]}>
            {mine ? (
              <View style={styles.userBubble} testID={`bubble-${message.id}`}>
                <Text style={styles.userText}>{message.text}</Text>
                <Text style={styles.userTime}>{message.at}</Text>
              </View>
            ) : (
              <View style={styles.aiBlock} testID={`ai-${message.id}`}>
                {message.demo ? <DemoPill /> : null}
                <Text style={[styles.aiText, message.error && styles.errorText]}>{message.text}</Text>
                {Array.isArray(message.citations) && message.citations.length > 0 ? (
                  <View style={styles.citations} testID={`citations-${message.id}`}>
                    {message.citations.map((cit, idx) => (
                      <View key={`${cit.fact_id}-${idx}`} style={styles.citationChip} testID={`citation-${cit.fact_id}`}>
                        <Text style={styles.citationId}>{cit.fact_id}</Text>
                        <Text style={styles.citationText}>{cit.text}</Text>
                      </View>
                    ))}
                  </View>
                ) : null}
                <Text style={styles.aiTime}>{message.at}</Text>
                <MemoryIngestedBadge confirmed={message.ingested} detail={message.ingestDetail} />
              </View>
            )}
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  list: {
    gap: spacing.lg,
  },
  row: {
    ...noShadow,
  },
  rowUser: {
    alignItems: "flex-end",
  },
  rowAi: {
    alignItems: "flex-start",
  },
  userBubble: {
    ...noShadow,
    backgroundColor: colors.userBubble,
    borderRadius: radii.card,
    maxWidth: "88%",
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
  },
  userText: {
    color: colors.onUserBubble,
    fontSize: typography.body,
  },
  userTime: {
    color: "rgba(255,255,255,0.72)",
    fontSize: 11,
    marginTop: spacing.xs,
  },
  aiBlock: {
    ...noShadow,
    backgroundColor: "transparent",
    gap: spacing.sm,
    maxWidth: "92%",
  },
  aiText: {
    color: colors.ink,
    fontSize: typography.body,
    lineHeight: 22,
  },
  errorText: {
    color: "#B3261E",
  },
  citations: {
    gap: spacing.xs,
  },
  citationChip: {
    ...noShadow,
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radii.chip,
    borderWidth: 1,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
  },
  citationId: {
    color: colors.gold.primary,
    fontSize: 11,
    fontWeight: "700",
  },
  citationText: {
    color: colors.ink,
    fontSize: typography.caption,
  },
  aiTime: {
    color: colors.muted,
    fontSize: 11,
  },
});
