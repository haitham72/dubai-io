"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import {
  Bell, ChevronLeft, Globe, Home, MoreHorizontal, Paperclip, PenLine, Search, Send, Sparkles, UserRound, Users,
} from "lucide-react";
import PostCard from "@/components/PostCard";
import { desktopPosts, jlt, phonePosts, suggested, type FeedCard } from "@/lib/feedFixture";

type Sort = "new" | "top" | "hot";
type Lane = "foryou" | "following";

const tabs = [
  { href: "/", label: "Home", icon: Home },
  { href: "/communities", label: "Communities", icon: Users },
  { href: "/create", label: "Create", icon: PenLine },
  { href: "/inbox", label: "Inbox", icon: Bell },
  { href: "/profile", label: "Me", icon: UserRound },
];

function sortPosts(posts: FeedCard[], sort: Sort) {
  const copy = [...posts];
  if (sort === "top") copy.sort((a, b) => b.votes - a.votes);
  if (sort === "hot") copy.sort((a, b) => b.comments - a.comments);
  return copy;
}

export default function FeedScreen() {
  const [sort, setSort] = useState<Sort>("new");
  const [lane, setLane] = useState<Lane>("foryou");
  const phone = useMemo(() => sortPosts(phonePosts, sort), [sort]);
  const desktop = useMemo(() => {
    const base = lane === "following" ? desktopPosts.filter((p) => p.followed) : desktopPosts;
    return sortPosts(base, sort);
  }, [lane, sort]);

  return (
    <>
      <div className="v2-phone">
        <header className="v2-topbar">
          <button type="button" className="v2-iconbtn" aria-label="Back"><ChevronLeft size={18} /></button>
          <div className="v2-iconrow">
            <button type="button" className="v2-iconbtn" aria-label="Search"><Search size={18} /></button>
            <button type="button" className="v2-iconbtn" aria-label="More"><MoreHorizontal size={18} /></button>
          </div>
        </header>
        <section className="v2-community">
          <img src={jlt.image} alt="JLT towers by the water, demo photo" />
          <div>
            <h1>{jlt.name}</h1>
            <p>{jlt.members}</p>
            <p>{jlt.blurb}</p>
          </div>
          <button type="button" className="v2-joined" aria-pressed="true">Joined</button>
        </section>
        <SortPills sort={sort} onSort={setSort} />
        {phone.map((post) => <PostCard key={post.id} post={post} header="person" />)}
        <nav className="v2-tabbar" aria-label="Primary">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const current = tab.href === "/";
            return (
              <Link key={tab.href} href={tab.href} className="v2-tab" aria-current={current ? "page" : undefined}>
                <span className="v2-tabicon"><Icon size={18} aria-hidden="true" /></span>
                {tab.label}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="v2-desktop">
        <aside className="v2-nav">
          <Link href="/" className="v2-logo">Dubai-io</Link>
          <Link href="/" className="v2-navlink" aria-current="page"><Home size={18} aria-hidden="true" />Home</Link>
          <Link href="/communities" className="v2-navlink"><Users size={18} aria-hidden="true" />Communities</Link>
          <a href="#ask" className="v2-navlink"><Sparkles size={18} aria-hidden="true" />Ask Dubai-io</a>
          <Link href="/inbox" className="v2-navlink"><Bell size={18} aria-hidden="true" />Inbox<span className="v2-badge">2</span></Link>
          <Link href="/profile" className="v2-navlink"><UserRound size={18} aria-hidden="true" />Me</Link>
          <Link href="/create" className="v2-postbtn"><PenLine size={18} aria-hidden="true" />Post</Link>
        </aside>
        <main>
          <div className="v2-centerhead">
            <div className="v2-tabs" role="tablist" aria-label="Feed">
              <button type="button" className="v2-tabtext" role="tab" aria-selected={lane === "foryou"} onClick={() => setLane("foryou")}>For you</button>
              <button type="button" className="v2-tabtext" role="tab" aria-selected={lane === "following"} onClick={() => setLane("following")}>Following</button>
            </div>
            <SortPills sort={sort} onSort={setSort} />
            <label className="v2-search">
              <Search size={16} aria-hidden="true" />
              <input type="search" placeholder="Search communities, posts or ask anything..." aria-label="Search" />
            </label>
          </div>
          {desktop.map((post) => <PostCard key={post.id} post={post} header="community" />)}
        </main>
        <aside className="v2-rail">
          <section className="v2-railcard" id="ask">
            <div className="v2-askrow">
              <h2>Ask Dubai-io privately</h2>
              <span className="v2-demo">Demo data</span>
            </div>
            <p className="v2-meta">Get local advice, plan things, check latest info.</p>
            <input className="v2-askbox" placeholder="Ask anything about life in Dubai..." aria-label="Ask Dubai-io privately" />
            <div className="v2-asktools">
              <button type="button" className="v2-tool"><Paperclip size={14} aria-hidden="true" />Attach</button>
              <button type="button" className="v2-tool"><Globe size={14} aria-hidden="true" />Web search</button>
              <button type="button" className="v2-ask"><Send size={14} aria-hidden="true" />Ask</button>
            </div>
          </section>
          <section className="v2-railcard">
            <div className="v2-askrow">
              <h2>Communities for you</h2>
              <span className="v2-demo">Demo data</span>
            </div>
            {suggested.map((group) => (
              <div className="v2-suggest" key={group.name}>
                <img src={group.image} alt="" />
                <div>
                  <strong>{group.name}</strong>
                  <span>{group.members}</span>
                  <span>{group.blurb}</span>
                </div>
                <button type="button" className="v2-join">Join</button>
              </div>
            ))}
            <Link href="/communities" className="v2-more">Discover more communities →</Link>
          </section>
        </aside>
      </div>
    </>
  );
}

function SortPills({ sort, onSort }: { sort: Sort; onSort: (sort: Sort) => void }) {
  const items: { id: Sort; label: string }[] = [
    { id: "new", label: "New" },
    { id: "top", label: "Top" },
    { id: "hot", label: "Hot" },
  ];
  return (
    <div className="v2-pills" role="tablist" aria-label="Sort">
      {items.map((item) => (
        <button key={item.id} type="button" className="v2-pill" role="tab" aria-selected={sort === item.id} onClick={() => onSort(item.id)}>
          {item.label}
        </button>
      ))}
    </div>
  );
}
