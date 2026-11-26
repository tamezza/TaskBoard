// Paper stock for the folders. A board keeps its colour for life,
// because the colour only depends on its id.
const FOLDER_COLOURS = ["#f0c674", "#f2a68f", "#b9cf9f", "#a9cbe0", "#cdb6e0"];

export function folderColour(boardId: number): string {
  return FOLDER_COLOURS[boardId % FOLDER_COLOURS.length];
}