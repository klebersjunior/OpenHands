import { FileClient } from "@openhands/typescript-client/clients";
import { getAgentServerClientOptions } from "#/api/agent-server-client-options";
import {
  isValidWorkspaceFolderName,
  joinBrowsePath,
} from "./folder-browser-paths";

/** Hidden placeholder so `/api/file/upload` mkdir -p's the new folder. */
export const HOST_DIRECTORY_PLACEHOLDER_FILE = ".gitkeep";

type FileUploadClientLike = Pick<FileClient, "uploadTextFile">;

export async function createHostDirectory(
  parentPath: string,
  name: string,
  fileClient: FileUploadClientLike = new FileClient(
    getAgentServerClientOptions(),
  ),
): Promise<string> {
  if (!isValidWorkspaceFolderName(name)) {
    throw new Error("Invalid folder name");
  }
  const destination = joinBrowsePath(parentPath, name.trim());
  // `/api/file/upload?path=` is the absolute *file* path. The server
  // mkdir -p's the parent, so writing `.gitkeep` inside the new folder
  // creates the directory. Passing the folder itself writes a file there
  // and the next search_subdirs returns 400 "Path is not a directory".
  const placeholderPath = joinBrowsePath(
    destination,
    HOST_DIRECTORY_PLACEHOLDER_FILE,
  );
  await fileClient.uploadTextFile(
    "",
    placeholderPath,
    HOST_DIRECTORY_PLACEHOLDER_FILE,
  );
  return destination;
}
