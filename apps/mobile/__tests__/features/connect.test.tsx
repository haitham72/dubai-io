import React from "react";
import { fireEvent, render, waitFor } from "@testing-library/react-native";
import * as SecureStore from "expo-secure-store";
import * as WebBrowser from "expo-web-browser";
import * as DocumentPicker from "expo-document-picker";
import { ConnectScreen } from "../../src/features/connect/ConnectScreen";
import { YoutubeOnboardingCard } from "../../src/features/connect/YoutubeOnboardingCard";
import { WhatsappImportCard } from "../../src/features/connect/WhatsappImportCard";

jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(async () => null),
  setItemAsync: jest.fn(async () => undefined),
  deleteItemAsync: jest.fn(async () => undefined),
}));
jest.mock("expo-web-browser", () => ({
  openAuthSessionAsync: jest.fn(async () => ({ type: "success" })),
}));
jest.mock("expo-document-picker", () => ({
  getDocumentAsync: jest.fn(),
}));

const picker = DocumentPicker.getDocumentAsync as jest.Mock;
const okFetcher = async () => ({ ok: true, status: 200, json: async () => ({}) });

beforeEach(() => { jest.clearAllMocks(); });

test("localhost warning appears for localhost and 127.0.0.1, not for LAN IP", async () => {
  const screen = await render(<ConnectScreen apiBaseUrl="http://192.168.1.10:8000" owner="karim" fetcher={okFetcher} />);
  expect(screen.queryByText(/cannot reach localhost/)).toBeNull();
  await fireEvent.changeText(screen.getByDisplayValue("http://192.168.1.10:8000"), "http://localhost:8000");
  expect(screen.getByText(/cannot reach localhost/)).toBeTruthy();
  await fireEvent.changeText(screen.getByDisplayValue("http://localhost:8000"), "http://127.0.0.1:8000");
  expect(screen.getByText(/cannot reach localhost/)).toBeTruthy();
});

test("Test Connection is honest: offline on failure, reachable only on success", async () => {
  const offline = await render(<ConnectScreen apiBaseUrl="http://192.168.1.10:8000" owner="karim"
    fetcher={async () => { throw new Error("down"); }} />);
  await fireEvent.press(offline.getByText("Test Connection"));
  await waitFor(() => expect(offline.getByText(/Offline/)).toBeTruthy());
  expect(offline.queryByText("Server reachable")).toBeNull();

  const online = await render(<ConnectScreen apiBaseUrl="http://192.168.1.10:8000" owner="karim" fetcher={okFetcher} />);
  await fireEvent.press(online.getByText("Test Connection"));
  await waitFor(() => expect(online.getByText("Server reachable")).toBeTruthy());
});

test("Save persists settings via SecureStore", async () => {
  const screen = await render(<ConnectScreen apiBaseUrl="http://192.168.1.10:8000" owner="karim" fetcher={okFetcher} />);
  await fireEvent.press(screen.getByText("Save settings"));
  await waitFor(() => expect(SecureStore.setItemAsync).toHaveBeenCalled());
});

test("signed-out Connect has no source toggles and no client secret anywhere", async () => {
  const screen = await render(<ConnectScreen apiBaseUrl="http://192.168.1.10:8000" fetcher={okFetcher} />);
  expect(screen.getByTestId("sources-signed-out")).toBeTruthy();
  expect(screen.queryByTestId("consent-gmail")).toBeNull();
  expect(screen.queryByText("Connect Google")).toBeNull();
});

test("EEA shows Data Portability, UAE shows Takeout-to-Drive, region persists", async () => {
  const screen = await render(<YoutubeOnboardingCard apiBaseUrl="http://192.168.1.10:8000" sessionToken="tok" initialRegion="UAE" fetcher={okFetcher} />);
  expect(screen.getByText(/Add to Drive/)).toBeTruthy();
  expect(screen.getByText(/Waiting for first Takeout drop in Drive/)).toBeTruthy();
  expect(screen.getByText(/sensitive topics are held back/)).toBeTruthy();
  expect(screen.queryByText(/Data Portability API/)).toBeNull();
  await fireEvent.press(screen.getByText("EEA / UK / Switzerland"));
  expect(screen.getByText(/Data Portability API/)).toBeTruthy();
  await waitFor(() => expect(SecureStore.setItemAsync).toHaveBeenCalledWith("dubaiio.youtubeRegion", "EEA"));
});

test("Takeout picker cancel does nothing; success uploads", async () => {
  picker.mockResolvedValueOnce({ canceled: true, assets: [] });
  const fetcher = jest.fn(okFetcher);
  const screen = await render(<YoutubeOnboardingCard apiBaseUrl="http://192.168.1.10:8000" sessionToken="tok" initialRegion="UAE" fetcher={fetcher} />);
  await fireEvent.press(screen.getByText("Upload Takeout JSON/ZIP now"));
  await waitFor(() => expect(picker).toHaveBeenCalled());
  expect(fetcher).not.toHaveBeenCalled();
  expect(screen.getByText(/Not connected/)).toBeTruthy();

  picker.mockResolvedValueOnce({ canceled: false, assets: [{ name: "watch-history.json", uri: "file:///w.json" }] });
  await fireEvent.press(screen.getByText("Upload Takeout JSON/ZIP now"));
  await waitFor(() => expect(screen.getByText(/Takeout uploaded/)).toBeTruthy());
  expect(fetcher).toHaveBeenCalled();
});

test("WhatsApp picker: .txt happy path, non-txt rejected, cancel is a no-op", async () => {
  const fetcher = jest.fn(okFetcher);
  const screen = await render(<WhatsappImportCard apiBaseUrl="http://192.168.1.10:8000" sessionToken="tok" fetcher={fetcher} />);
  picker.mockResolvedValueOnce({ canceled: false, assets: [{ name: "chat.pdf", uri: "file:///c.pdf" }] });
  await fireEvent.press(screen.getByText("Pick WhatsApp .txt export"));
  await waitFor(() => expect(screen.getByText(/must be .txt/)).toBeTruthy());
  expect(fetcher).not.toHaveBeenCalled();

  picker.mockResolvedValueOnce({ canceled: true, assets: [] });
  await fireEvent.press(screen.getByText("Pick WhatsApp .txt export"));
  await waitFor(() => expect(picker).toHaveBeenCalledTimes(2));
  expect(fetcher).not.toHaveBeenCalled();

  picker.mockResolvedValueOnce({ canceled: false, assets: [{ name: "chat.txt", uri: "file:///c.txt" }] });
  await fireEvent.press(screen.getByText("Pick WhatsApp .txt export"));
  await waitFor(() => expect(screen.getByText(/Uploaded chat.txt/)).toBeTruthy());
  expect(fetcher).toHaveBeenCalled();
});
