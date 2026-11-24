/** Typed WebView <-> Expo native bridge for microphone permissions, voice recording, and media/sticker picking. */

export type MediaPickFilter = "images" | "videos" | "all";

export type BridgeRequest =
  | { type: "REQUEST_MIC"; requestId?: string }
  | { type: "START_VOICE_RECORDING"; requestId?: string }
  | { type: "STOP_VOICE_RECORDING"; requestId?: string }
  | { type: "PICK_MEDIA"; requestId?: string; allowsEditing?: boolean; mediaTypes?: MediaPickFilter }
  | { type: "PICK_STICKER"; requestId?: string };

export interface BridgePickedAsset {
  uri: string;
  mimeType?: string;
  width?: number;
  height?: number;
  fileName?: string;
  base64?: string;
}

export type BridgeResponse =
  | {
      type: "MIC_PERMISSION_RESULT";
      requestId?: string;
      granted: boolean;
      status: string;
      canAskAgain?: boolean;
    }
  | {
      type: "VOICE_RECORDING_RESULT";
      requestId?: string;
      status: "started" | "stopped" | "error";
      uri?: string;
      durationMs?: number;
      error?: string;
    }
  | {
      type: "MEDIA_PICKED";
      requestId?: string;
      mode: "media" | "sticker";
      canceled: boolean;
      assets: BridgePickedAsset[];
      error?: string;
    };

const VALID_MEDIA_FILTERS = new Set<MediaPickFilter>(["images", "videos", "all"]);
const MAX_MESSAGE_BYTES = 16 * 1024;
const MAX_REQUEST_ID_LENGTH = 128;

function sanitizeRequestId(value: unknown): string | undefined {
  if (typeof value !== "string") return undefined;
  const trimmed = value.trim();
  if (!trimmed || trimmed.length > MAX_REQUEST_ID_LENGTH) return undefined;
  return trimmed;
}

/** Validate and parse a JSON message sent from the WebView via window.ReactNativeWebView.postMessage. */
export function parseBridgeRequest(raw: string): BridgeRequest | null {
  if (typeof raw !== "string" || !raw || raw.length > MAX_MESSAGE_BYTES) {
    return null;
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }

  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    return null;
  }

  const record = parsed as Record<string, unknown>;
  const type = record.type;
  if (typeof type !== "string") return null;

  const requestId = sanitizeRequestId(record.requestId);

  switch (type) {
    case "REQUEST_MIC":
      return requestId ? { type, requestId } : { type };
    case "START_VOICE_RECORDING":
      return requestId ? { type, requestId } : { type };
    case "STOP_VOICE_RECORDING":
      return requestId ? { type, requestId } : { type };
    case "PICK_STICKER":
      return requestId ? { type, requestId } : { type };
    case "PICK_MEDIA": {
      const allowsEditing = typeof record.allowsEditing === "boolean" ? record.allowsEditing : undefined;
      const mediaTypes =
        typeof record.mediaTypes === "string" && VALID_MEDIA_FILTERS.has(record.mediaTypes as MediaPickFilter)
          ? (record.mediaTypes as MediaPickFilter)
          : undefined;
      const out: BridgeRequest = { type };
      if (requestId) out.requestId = requestId;
      if (allowsEditing !== undefined) out.allowsEditing = allowsEditing;
      if (mediaTypes !== undefined) out.mediaTypes = mediaTypes;
      return out;
    }
    default:
      return null;
  }
}

/** Serialize a native bridge response into safe JavaScript executed inside the WebView. */
export function serializeBridgeEventToJs(event: BridgeResponse): string {
  const json = JSON.stringify(event)
    .replace(/</g, "\\u003c")
    .replace(/>/g, "\\u003e")
    .replace(/\u2028/g, "\\u2028")
    .replace(/\u2029/g, "\\u2029");
  return `(function(){try{var d=${json};window.dispatchEvent(new CustomEvent("messenger:native",{detail:d}));if(window.__messengerMobileBridge&&typeof window.__messengerMobileBridge._resolve==="function"){window.__messengerMobileBridge._resolve(d);}}catch(e){}})();true;`;
}

/** JavaScript injected before content loads so the web app can invoke native mic/media capabilities cleanly. */
export function buildWebViewBridgeScript(): string {
  return `(function(){
  if (window.__messengerMobileBridge) return;
  var pending = Object.create(null);
  var seq = 0;
  function send(type, extra) {
    return new Promise(function(resolve, reject) {
      if (!window.ReactNativeWebView || typeof window.ReactNativeWebView.postMessage !== "function") {
        reject(new Error("ReactNativeWebView bridge unavailable"));
        return;
      }
      var requestId = "mg_" + (++seq) + "_" + Date.now();
      pending[requestId] = resolve;
      var payload = Object.assign({ type: type, requestId: requestId }, extra || {});
      window.ReactNativeWebView.postMessage(JSON.stringify(payload));
    });
  }
  window.__messengerMobileBridge = {
    isNativeShell: true,
    requestMic: function() { return send("REQUEST_MIC"); },
    startVoiceRecording: function() { return send("START_VOICE_RECORDING"); },
    stopVoiceRecording: function() { return send("STOP_VOICE_RECORDING"); },
    pickMedia: function(opts) { return send("PICK_MEDIA", opts || {}); },
    pickSticker: function() { return send("PICK_STICKER"); },
    _resolve: function(detail) {
      if (detail && detail.requestId && pending[detail.requestId]) {
        var fn = pending[detail.requestId];
        delete pending[detail.requestId];
        fn(detail);
      }
    }
  };
})();true;`;
}
