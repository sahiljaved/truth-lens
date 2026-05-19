import client from "./client";

export async function uploadFile(file, fileType) {
  const form = new FormData();
  form.append("file", file);
  form.append("file_type", fileType);
  const { data } = await client.post("/upload/", form);
  return data.upload;
}

export async function uploadText(rawText) {
  const { data } = await client.post("/upload/", {
    raw_text: rawText,
    file_type: "text",
  });
  return data.upload;
}

export async function startVerification(uploadId) {
  const { data } = await client.post("/verify/", { upload_id: uploadId });
  return data;
}

export async function pollUpload(uploadId) {
  const { data } = await client.get(`/upload/${uploadId}/`);
  return data;
}
