import React, { type ComponentType } from "react";
import { ConnectScreen } from "../features/connect/ConnectScreen";
import { QuestsScreen } from "../features/quests/QuestsScreen";
import { VaultScreen } from "../features/vault/VaultScreen";
import type { ConnectScreenProps, QuestsScreenProps, VaultScreenProps } from "./types";

const MountedVaultScreen: ComponentType<VaultScreenProps> = ({ ownerId, apiBaseUrl, demo }) =>
  React.createElement(VaultScreen, { owner: ownerId, apiBaseUrl, demo });

const MountedQuestsScreen: ComponentType<QuestsScreenProps> = ({ ownerId, apiBaseUrl }) =>
  React.createElement(QuestsScreen, { owner: ownerId, apiBaseUrl });

const MountedConnectScreen: ComponentType<ConnectScreenProps> = ({ ownerId, apiBaseUrl }) =>
  React.createElement(ConnectScreen, { owner: ownerId, apiBaseUrl });

export const vaultScreen: ComponentType<VaultScreenProps> | null = MountedVaultScreen;
export const questsScreen: ComponentType<QuestsScreenProps> | null = MountedQuestsScreen;
export const connectScreen: ComponentType<ConnectScreenProps> | null = MountedConnectScreen;
