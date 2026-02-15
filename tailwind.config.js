/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './apps/**/templates/**/*.html',
    './apps/**/*.py', // Para classes definidas em forms.py ou views.py
  ],
  theme: {
    extend: {},
  },
  plugins: [
    require("daisyui")
  ],
  daisyui: {
    themes: ["cupcake"], // Mantém apenas o tema light para reduzir o tamanho do ficheiro final
  },
}
