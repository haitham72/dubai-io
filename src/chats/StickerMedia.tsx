// A sticker image or an animated one: .webm plays muted and looped like Telegram video stickers.
export function StickerMedia({ url, alt = "Sticker", onLoad }: { url: string; alt?: string; onLoad?: () => void }) {
  return /\.webm(\?|$)/i.test(url)
    ? <video src={url} autoPlay loop muted playsInline aria-label={alt} onLoadedMetadata={onLoad} />
    : <img src={url} alt={alt} loading="lazy" onLoad={onLoad} />;
}
