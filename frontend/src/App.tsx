import { useState } from "react";
import { sendAudio } from "./api";

export default function App() {
  const [text, setText] = useState("");

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    if (!e.target.files?.length) return;
    const file = e.target.files[0];
    const result = await sendAudio(file);
    setText(result.transcript);
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">ATC Voice Loop Demo</h1>
      <input type="file" accept="audio/*" onChange={handleFile} />
      <p className="mt-4 text-lg">{text}</p>
    </div>
  );
}
