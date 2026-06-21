import "./globals.css";

export const metadata = {
  title: "CUSB RAG",
  description: "Citation-grounded CUSB chatbot"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

