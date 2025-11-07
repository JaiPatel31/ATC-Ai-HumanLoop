# Conflict Resolution UI Testing Branch

This branch (`conflict-resolution-ui-testing`) packages the conflict resolution dashboard
and aircraft tracking updates so they can be validated in isolation from other work in
progress.

## Contents
- Updated ATC loop interface with the conflict resolution side panel.
- Aircraft state derivation and basic conflict detection heuristics.
- Styled dashboard components and supporting shared types.

## Getting started
1. Install dependencies in the frontend package if you have not already:
   ```bash
   cd frontend
   npm install
   ```
2. Build the React application to ensure everything compiles:
   ```bash
   npm run build
   ```
3. Start the development server to explore the UI:
   ```bash
   npm run dev
   ```

## Notes
- The branch tracks the voice loop enhancements shipped previously, so
  any regressions or issues you spot should be reported against this branch.
- Backend APIs remain unchanged; only the frontend experience is included here.

