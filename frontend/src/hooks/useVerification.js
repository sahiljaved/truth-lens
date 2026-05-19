import { useCallback, useRef, useState } from "react";
import {
  pollUpload,
  startVerification,
  uploadFile,
  uploadText,
} from "../api/verifier";

const POLL_INTERVAL_MS = 2500;
const MAX_POLLS = 60;

export default function useVerification() {
  const [phase, setPhase] = useState("idle");
  const [error, setError] = useState(null);
  const [upload, setUpload] = useState(null);
  const [result, setResult] = useState(null);
  const pollTimer = useRef(null);

  const reset = useCallback(() => {
    if (pollTimer.current) clearInterval(pollTimer.current);
    setPhase("idle");
    setError(null);
    setUpload(null);
    setResult(null);
  }, []);

  const pollUntilDone = useCallback((uploadId) => {
    let attempts = 0;
    pollTimer.current = setInterval(async () => {
      attempts += 1;
      try {
        const data = await pollUpload(uploadId);
        setUpload(data);
        if (data.status === "completed" && data.result) {
          clearInterval(pollTimer.current);
          setResult(data.result);
          setPhase("done");
        } else if (data.status === "failed") {
          clearInterval(pollTimer.current);
          setError("Verification failed. Please try again.");
          setPhase("error");
        } else if (attempts >= MAX_POLLS) {
          clearInterval(pollTimer.current);
          setError("Verification is taking too long. Please try again later.");
          setPhase("error");
        }
      } catch (err) {
        clearInterval(pollTimer.current);
        setError(err.message || "Polling failed");
        setPhase("error");
      }
    }, POLL_INTERVAL_MS);
  }, []);

  const submitFile = useCallback(
    async (file, fileType) => {
      reset();
      setPhase("uploading");
      try {
        const created = await uploadFile(file, fileType);
        setUpload(created);
        setPhase("verifying");
        await startVerification(created.id);
        setPhase("polling");
        pollUntilDone(created.id);
      } catch (err) {
        setError(err.message || "Upload failed");
        setPhase("error");
      }
    },
    [pollUntilDone, reset]
  );

  const submitText = useCallback(
    async (text) => {
      reset();
      setPhase("uploading");
      try {
        const created = await uploadText(text);
        setUpload(created);
        setPhase("verifying");
        await startVerification(created.id);
        setPhase("polling");
        pollUntilDone(created.id);
      } catch (err) {
        setError(err.message || "Submission failed");
        setPhase("error");
      }
    },
    [pollUntilDone, reset]
  );

  return { phase, error, upload, result, submitFile, submitText, reset };
}
