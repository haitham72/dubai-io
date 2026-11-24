import React from "react";
import { fireEvent, render, waitFor } from "@testing-library/react-native";
import { mapPairingErrorCode, parsePairingScan, validatePairingApiBase } from "../src/lib/auth";
import { ScanQrModal } from "../src/features/connect/QrPairingModals";

jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(async () => null),
  setItemAsync: jest.fn(async () => undefined),
  deleteItemAsync: jest.fn(async () => undefined),
}));
jest.mock("expo-web-browser", () => ({ openAuthSessionAsync: jest.fn() }));
jest.mock("expo-camera", () => ({
  CameraView: () => null,
  useCameraPermissions: () => [{ granted: false }, jest.fn()],
}));

describe("QR payload with the API address", () => {
  it("reads code and api from the QR; manual code has no api", () => {
    const scan = parsePairingScan("dubaiio://pair?code=ab12cd34&api=http%3A%2F%2F192.168.1.20%3A8000");
    expect(scan).toEqual({ code: "AB12CD34", apiBase: "http://192.168.1.20:8000" });
    expect(parsePairingScan("dubaiio://pair?code=ZZ1")).toEqual({ code: "ZZ1", apiBase: null });
    expect(parsePairingScan("abcd2345")).toEqual({ code: "ABCD2345", apiBase: null });
  });

  it("accepts https anywhere and http only to localhost or private LAN", () => {
    for (const ok of [
      "http://localhost:8000",
      "http://127.0.0.1:8000/",
      "http://10.1.2.3:8000",
      "http://172.16.0.5:8000",
      "http://172.31.255.1:8000",
      "http://192.168.0.7:8000",
      "https://api.example.test",
    ]) {
      expect(validatePairingApiBase(ok)).not.toBeNull();
    }
    expect(validatePairingApiBase("http://192.168.1.20:8000/")).toBe("http://192.168.1.20:8000");
    for (const bad of [
      "http://evil.example.test",
      "http://8.8.8.8:8000",
      "http://172.32.0.1:8000",
      "http://172.15.0.1:8000",
      "http://192.169.0.1",
      "http://11.0.0.1",
      "ftp://192.168.1.1",
      "javascript:alert(1)",
      "http://user:pw@192.168.1.1",
      "not a url",
    ]) {
      expect(validatePairingApiBase(bad)).toBeNull();
    }
  });

  it("maps lockout responses to a clear message", () => {
    expect(mapPairingErrorCode("too_many_attempts", 429)).toMatch(/too many/i);
    expect(mapPairingErrorCode(undefined, 429)).toMatch(/too many/i);
  });
});

describe("ScanQrModal", () => {
  const QR = (api: string) => `dubaiio://pair?code=ABCD2345&api=${encodeURIComponent(api)}`;

  it("manual entry still works and passes no api address", async () => {
    const onSubmit = jest.fn(async () => undefined);
    const view = await render(<ScanQrModal visible onSubmitCode={onSubmit} onClose={jest.fn()} />);
    await fireEvent.changeText(view.getByTestId("pair-code-input"), "abcd2345");
    await fireEvent.press(view.getByTestId("pair-submit-btn"));
    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith("ABCD2345", undefined));
  });

  it("a pasted QR with a LAN address passes the validated base", async () => {
    const onSubmit = jest.fn(async () => undefined);
    const view = await render(<ScanQrModal visible onSubmitCode={onSubmit} onClose={jest.fn()} />);
    await fireEvent.changeText(view.getByTestId("pair-code-input"), QR("http://192.168.1.20:8000/"));
    await fireEvent.press(view.getByTestId("pair-submit-btn"));
    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith("ABCD2345", "http://192.168.1.20:8000"));
  });

  it("refuses a QR that points at a public http address with an honest error", async () => {
    const onSubmit = jest.fn(async () => undefined);
    const view = await render(<ScanQrModal visible onSubmitCode={onSubmit} onClose={jest.fn()} />);
    await fireEvent.changeText(view.getByTestId("pair-code-input"), QR("http://evil.example.test"));
    await fireEvent.press(view.getByTestId("pair-submit-btn"));
    expect((await view.findByTestId("pair-error")).props.children).toMatch(/will not trust/i);
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
