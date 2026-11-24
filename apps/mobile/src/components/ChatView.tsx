import React, { useEffect, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { colors, noShadow, radii, spacing, typography } from "@dubai-io/design-tokens";
import { postChatTurn } from "../lib/api";
import { useApiSettingsOptional } from "../lib/api-settings";
import { useAuthOptional } from "../lib/auth";
import { demoAction, demoRepair, demoThread } from "../lib/fixtures";
import type { ChatMessage, MemoryTurnConfirmation, RepairPing } from "../lib/types";
import { ChatMessageList } from "./ChatMessageList";
import { DemoPill } from "./DemoPill";
import { LifeDrawer } from "./LifeDrawer";
import { ProactiveRepairCard } from "./ProactiveRepairCard";

export function ChatView({
  ownerId: propOwnerId,
  apiBaseUrl: propApiBaseUrl,
  sessionToken: propSessionToken,
  demo: propDemo,
  threadId = "default",
  sendTurn,
  initialMessages,
  repair,
}: {
  ownerId?: string;
  apiBaseUrl?: string;
  sessionToken?: string | null;
  demo?: boolean;
  threadId?: string;
  sendTurn?: (text: string) => Promise<MemoryTurnConfirmation>;
  initialMessages?: ChatMessage[];
  repair?: RepairPing | null;
}) {
  const auth = useAuthOptional();
  const apiSettings = useApiSettingsOptional();

  const demo = propDemo ?? auth?.demoMode ?? false;
  const apiBaseUrl = propApiBaseUrl ?? apiSettings?.apiBaseUrl ?? "";
  const sessionToken = propSessionToken !== undefined ? propSessionToken : auth?.session?.sessionToken ?? null;
  const ownerId = propOwnerId ?? (demo ? "karim" : auth?.session?.userId ?? "");
  const effectiveInitialMessages = initialMessages ?? (demo ? demoThread : []);
  const effectiveRepair = repair !== undefined ? repair : demo ? demoRepair : null;

  const [messages, setMessages] = useState<ChatMessage[]>(effectiveInitialMessages);
  const [draft, setDraft] = useState("");
  const [accepted, setAccepted] = useState(false);
  const [drawer, setDrawer] = useState(false);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (initialMessages === undefined) {
      setMessages(demo ? demoThread : []);
    }
  }, [demo, initialMessages]);

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
        : await postChatTurn(apiBaseUrl, { text, threadId, sessionToken, demo });

      if (!turn.ok && turn.error && !turn.demo) {
        setMessages((current) => [
          ...current,
          {
            id: `a-err-${messages.length + 1}`,
            role: "assistant",
            text: turn.error ?? "Chat request failed. Nothing was ingested.",
            at: "now",
            ingested: false,
            error: true,
            demo: false,
          },
        ]);
        return;
      }

      const confirmed = turn.ingested === true || turn.applied === true || (turn.ok === true && !turn.demo);
      const metaParts = [
        turn.trust ? `trust: ${turn.trust}` : null,
        turn.topic ? `topic: ${turn.topic}` : null,
        turn.model ? `model: ${turn.model}` : null,
      ].filter(Boolean);
      const detail = confirmed && metaParts.length > 0 ? metaParts.join(" · ") : undefined;
      const assistant: ChatMessage = {
        id: `a-${messages.length + 1}`,
        role: "assistant",
        text: turn.reply || "The service returned no text.",
        at: "now",
        ingested: confirmed,
        ingestDetail: detail,
        citations: turn.citations,
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
          error: true,
          demo: false,
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
          {ownerId && !demo ? <Text style={styles.subBrand}>{auth?.session?.displayName ?? ownerId}</Text> : null}
        </View>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Life categories"
          onPress={() => setDrawer(true)}
          testID="open-life-drawer"
        >
          <Text style={styles.more}>···</Text>
        </Pressable>
      </View>
      <ScrollView contentContainerStyle={styles.thread}>
        {!demo && !sessionToken && !sendTurn ? (
          <View style={styles.notice} testID="chat-auth-notice">
            <Text style={styles.noticeTitle}>Sign in required</Text>
            <Text style={styles.noticeBody}>
              Sign in with Google or pair your iPhone on Connect to chat with your real memory.
            </Text>
          </View>
        ) : null}
        <ChatMessageList messages={messages} />
        {effectiveRepair ? (
          <ProactiveRepairCard ping={effectiveRepair} accepted={accepted} onAccept={() => setAccepted(true)} />
        ) : null}
        {demo ? (
          <View style={styles.action} testID="action-card">
            {demoAction.demo ? <DemoPill /> : null}
            <Text style={styles.actionTitle}>{demoAction.title}</Text>
            <Text style={styles.actionSub}>{demoAction.subtitle}</Text>
          </View>
        ) : null}
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
  subBrand: {
    color: colors.muted,
    fontSize: typography.caption,
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
  notice: {
    ...noShadow,
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radii.card,
    borderWidth: 1,
    gap: spacing.xs,
    padding: spacing.lg,
  },
  noticeTitle: {
    color: colors.ink,
    fontWeight: "700",
    fontSize: typography.body,
  },
  noticeBody: {
    color: colors.muted,
    fontSize: typography.caption,
    lineHeight: 18,
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
