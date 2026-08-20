import { invoke, Channel } from "@tauri-apps/api/core";

export interface ReplizAccount {
  id: string;
  name: string;
  username: string;
  type: string;
  is_connected: boolean;
}

export interface ReplizUploadResult {
  video_url: string;
  results: { account_id: string; success: boolean; message: string }[];
}

export type ReplizUploadEvent = { type: "log"; message: string };

export async function replizListAccounts(
  accessKey: string,
  secretKey: string
): Promise<ReplizAccount[]> {
  return invoke<ReplizAccount[]>("repliz_list_accounts", {
    accessKey,
    secretKey,
  });
}

export async function replizUpload(params: {
  accessKey: string;
  secretKey: string;
  videoPath: string;
  title: string;
  description: string;
  accountIds: string[];
  scheduleAt: string | null;
  onLog?: (message: string) => void;
}): Promise<ReplizUploadResult> {
  const channel = new Channel<ReplizUploadEvent>();
  if (params.onLog) {
    channel.onmessage = (event) => {
      if (event.type === "log") params.onLog!(event.message);
    };
  }

  return invoke<ReplizUploadResult>("repliz_upload", {
    accessKey: params.accessKey,
    secretKey: params.secretKey,
    videoPath: params.videoPath,
    title: params.title,
    description: params.description,
    accountIds: params.accountIds,
    scheduleAt: params.scheduleAt,
    onEvent: channel,
  });
}
