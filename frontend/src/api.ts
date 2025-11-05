export async function sendAudio(file: File) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("http://127.0.0.1:8000/stt", {
    method: "POST",
    body: form,
  });
  return res.json();
}
