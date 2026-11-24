// Flights workspace (R10). Owned by T04-flights (see prompts/llm2-workspaces.md → "Flights").
// Contract: export `flightsScreen` = { Sidebar?, Main } (see src/screens.ts). Keep the export name.
import { FlightsSidebar } from "./Sidebar";
import { FlightsMain } from "./Main";

export const flightsScreen = { Sidebar: FlightsSidebar, Main: FlightsMain };
