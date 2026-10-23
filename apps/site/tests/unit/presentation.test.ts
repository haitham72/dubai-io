import { expect, test } from "vitest";
import { presentation } from "../../unified/presentation";

test("plain URL is the website", () => expect(presentation("")).toBe("website"));
test("?desktop is the Mac window", () => expect(presentation("?desktop")).toBe("desktop"));
test("?device is the iPhone frame", () => expect(presentation("?device")).toBe("device"));
test("device wins when both are given", () => expect(presentation("?desktop&device")).toBe("device"));
