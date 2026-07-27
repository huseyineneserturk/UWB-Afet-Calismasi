document.addEventListener("DOMContentLoaded", () => {
  if (typeof mermaid === "undefined") {
    return;
  }

  const darkMode = window.matchMedia("(prefers-color-scheme: dark)").matches;

  mermaid.initialize({
    startOnLoad: false,
    securityLevel: "loose",
    theme: darkMode ? "dark" : "base",
    themeVariables: {
      primaryColor: darkMode ? "#164b61" : "#e8f7f8",
      primaryTextColor: darkMode ? "#f4f8fa" : "#0b2c3d",
      primaryBorderColor: "#16a6b6",
      lineColor: "#16a6b6",
      secondaryColor: darkMode ? "#4a2d21" : "#fff0e9",
      tertiaryColor: darkMode ? "#12232d" : "#f4f8fa",
      fontFamily: "Roboto, sans-serif"
    }
  });

  mermaid.run({ querySelector: ".mermaid" });
});
