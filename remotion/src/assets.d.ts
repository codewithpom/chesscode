declare module "*.woff2" {
  const src: string;
  export default src;
}
declare module "*.svg" {
  const src: string;
  export default src;
}
declare module "*.mp3" {
  const src: string;
  export default src;
}
// @types/react-dom is not installed; tests only need this one function.
declare module "react-dom/server" {
  export function renderToStaticMarkup(element: import("react").ReactElement): string;
}
