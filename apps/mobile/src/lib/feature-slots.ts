import type { ComponentType } from "react";
import type { ConnectScreenProps, QuestsScreenProps, VaultScreenProps } from "./types";

/**
 * I-B drop-in slots. Leave null until `src/features/{vault,quests,connect}` exists.
 * Then assign the exported screens (do not recreate those folders on this branch):
 *
 * import { VaultScreen } from "../features/vault";
 * import { QuestsScreen } from "../features/quests";
 * import { ConnectScreen } from "../features/connect";
 */
export const vaultScreen: ComponentType<VaultScreenProps> | null = null;
export const questsScreen: ComponentType<QuestsScreenProps> | null = null;
export const connectScreen: ComponentType<ConnectScreenProps> | null = null;
