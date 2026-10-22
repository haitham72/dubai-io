export interface SiteImage {
  src: string;
  alt: string;
  caption: string;
  credit: string;
  sourceUrl: string;
  license: string;
}

/**
 * Locally hosted, openly-licensed photographs. Every entry names the
 * creator, the license and the source page. Pictured people are not
 * affiliated with Dubai-io and do not endorse it.
 */
export const IMAGES: Record<string, SiteImage> = {
  skyline: {
    src: "/images/skyline-hero.jpg",
    alt: "Dubai skyline at dusk",
    caption: "Dubai skyline at dusk",
    credit: "Fariz Safarulla",
    sourceUrl: "https://www.flickr.com/photos/39380272@N07/16857714600",
    license: "CC BY-SA 2.0",
  },
  burj: {
    src: "/images/burj.jpg",
    alt: "Burj Khalifa rising above the city",
    caption: "Burj Khalifa, Downtown Dubai",
    credit: "jurvetson",
    sourceUrl: "https://www.flickr.com/photos/44124348109@N01/47956427896",
    license: "CC BY 2.0",
  },
  marina: {
    src: "/images/marina.jpg",
    alt: "Dubai Marina towers lit up at night",
    caption: "Dubai Marina at night",
    credit: "Iwona Rege",
    sourceUrl: "https://commons.wikimedia.org/w/index.php?curid=68363730",
    license: "CC BY-SA 4.0",
  },
  metro: {
    src: "/images/metro.jpg",
    alt: "Dubai Metro line running along Sheikh Zayed Road",
    caption: "Dubai Metro along Sheikh Zayed Road",
    credit: "travelourplanet.com",
    sourceUrl: "https://www.flickr.com/photos/63503049@N03/8973069052",
    license: "CC BY 2.0",
  },
  mezze: {
    src: "/images/mezze.jpg",
    alt: "Shared plates of mezze on a table",
    caption: "Mezze to share (illustrative)",
    credit: "twiga_swala",
    sourceUrl: "https://www.flickr.com/photos/21013862@N08/2254636467",
    license: "CC BY-SA 2.0",
  },
  souk: {
    src: "/images/souk.jpg",
    alt: "Spice sacks piled high at a souk stall",
    caption: "Spice souk (illustrative)",
    credit: "katinalynn",
    sourceUrl: "https://www.flickr.com/photos/76948127@N00/3429368234",
    license: "CC BY 2.0",
  },
  desert: {
    src: "/images/desert.jpg",
    alt: "Wind-shaped desert dunes",
    caption: "Desert dunes outside the city (illustrative)",
    credit: "roblerner",
    sourceUrl: "https://www.flickr.com/photos/47706097@N00/253203881",
    license: "CC BY 2.0",
  },
  morning: {
    src: "/images/morning.jpg",
    alt: "Dubai skyline in the morning light",
    caption: "Dubai skyline in the morning",
    credit: "Jay Tamboli",
    sourceUrl: "https://www.flickr.com/photos/47084925@N00/3040719389",
    license: "CC BY 2.0",
  },
};

