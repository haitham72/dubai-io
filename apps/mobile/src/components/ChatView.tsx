import React, { useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { colors, noShadow, radii, spacing, typography } from "@dubai-io/design-tokens";
import { postMemoryChatTurn } from "../lib/api";
import { demoAction, demoRepair, demoThread } from "../lib/fixtures";
import type { ChatMessage, MemoryTurnConfirmation, RepairPing } from "../lib/types";
import { ChatMessageList } from "./ChatMessageList";
import { DemoPill } from "./DemoPill";
import { LifeDrawer } from "./LifeDrawer";
import { ProactiveRepairCard } from "./ProactiveRepairCard";

export function ChatView({
  ownerId = "karim",
  apiBaseUrl = "",
  sendTurn,
  initialMessages = demoThread,
  repair = demoRepair,
}: {
  ownerId?: string;
  apiBaseUrl?: string;
  sendTurn?: (text: string) => Promise<MemoryTurnConfirmation>;
  initialMessages?: ChatMessage[];
  repair?: RepairPing;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [draft, setDraft] = useState("");
  const [accepted, setAccepted] = useState(false);
  const [drawer, setDrawer] = useState(false);
  const [sending, setSending] = useState(false);

  async function onSend() {
    const text = draft.trim();
    if (!text || sending) return;
    setDraft("");
    setSending(true);
    const userMessage: ChatMessage = {
      id: `u-${messages.length + 1}`,
      role: "user",
      text,
      at: "now",
      ingested: false,
      demo: false,
    };
    setMessages((current) => [...current, userMessage]);
    try {
      const turn = sendTurn
        ? await sendTurn(text)
        : await postMemoryChatTurn(apiBaseUrl, { ownerId, text });
      const confirmed = turn.applied === true || (turn.ok === true && !turn.demo);
      const detail = confirmed && turn.trust && turn.topic ? `trust: ${turn.trust} · topic: ${turn.topic}` : undefined;
      const assistant: ChatMessage = {
        id: `a-${messages.length + 1}`,
        role: "assistant",
        text: turn.reply || "The service returned no text.",
        at: "now",
        ingested: confirmed,
        ingestDetail: detail,
        demo: turn.demo,
      };
      setMessages((current) => [...current, assistant]);
    } catch {
      setMessages((current) => [
        ...current,
        {
          id: `a-error-${messages.length + 1}`,
          role: "assistant",
          text: "The memory service did not confirm this turn. Nothing was ingested.",
          at: "now",
          ingested: false,
          demo: true,
        },
      ]);
    } finally {
      setSending(false);
    }
  }

  return (
    <View style={styles.screen} testID="chat-screen">
      <View style={styles.header}>
        <View>
          <Text style={styles.brand}>Dubai-io Quest AI Companion</Text>
        </View>
        <Pressable accessibilityRole="button" accessibilityLabel="Life categories" onPress={() => setDrawer(true)} testID="open-life-drawer">
          <Text style={styles.more}>···</Text>
        </Pressable>
      </View>
      <ScrollView contentContainerStyle={styles.thread}>
        <ChatMessageList messages={messages} />
        <ProactiveRepairCard ping={repair} accepted={accepted} onAccept={() => setAccepted(true)} />
        <View style={styles.action} testID="action-card">
          {demoAction.demo ? <DemoPill /> : null}
          <Text style={styles.actionTitle}>{demoAction.title}</Text>
          <Text style={styles.actionSub}>{demoAction.subtitle}</Text>
        </View>
      </ScrollView>
      <View style={styles.composer}>
        <TextInput
          value={draft}
          onChangeText={setDraft}
          placeholder="Message Dubai-io..."
          placeholderTextColor={colors.muted}
          style={styles.input}
          testID="chat-input"
        />
        <Pressable accessibilityRole="button" onPress={onSend} style={styles.send} testID="chat-send">
          <Text style={styles.sendText}>Send</Text>
        </Pressable>
      </View>
      <LifeDrawer open={drawer} onClose={() => setDrawer(false)} />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    ...noShadow,
    backgroundColor: colors.canvas,
    flex: 1,
  },
  header: {
    alignItems: "center",
    borderBottomColor: colors.borderHairline,
    borderBottomWidth: 1,
    flexDirection: "row",
    justifyContent: "space-between",
    padding: spacing.lg,
  },
  brand: {
    color: colors.ink,
    fontFamily: typography.serif,
    fontSize: typography.body,
  },
  more: {
    color: colors.ink,
    fontSize: 22,
    letterSpacing: 2,
  },
  thread: {
    gap: spacing.lg,
    padding: spacing.lg,
    paddingBottom: 140,
  },
  action: {
    ...noShadow,
    backgroundColor: colors.actionBox,
    borderColor: colors.border,
    borderRadius: radii.card,
    borderWidth: 1,
    gap: spacing.xs,
    padding: spacing.lg,
  },
  actionTitle: {
    color: colors.ink,
    fontSize: typography.body,
    fontWeight: "600",
  },
  actionSub: {
    color: colors.muted,
    fontSize: typography.caption,
  },
  composer: {
    ...noShadow,
    alignItems: "center",
    backgroundColor: colors.canvas,
    borderColor: colors.border,
    borderRadius: radii.dock,
    borderWidth: 1,
    flexDirection: "row",
    gap: spacing.sm,
    margin: spacing.lg,
    padding: spacing.sm,
  },
  input: {
    color: colors.ink,
    flex: 1,
    fontSize: typography.body,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  send: {
    ...noShadow,
    backgroundColor: colors.gold.primary,
    borderRadius: radii.pill,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
  },
  sendText: {
    color: colors.canvas,
    fontWeight: "700",
  },
});
