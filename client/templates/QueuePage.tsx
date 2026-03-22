import React from "react";

import {Shell} from "@client/components/Shell";
import {templates} from "@client/schema";

type Props = templates.QueuePage;

const STATUS_LABELS: Record<string, string> = {
    pending: "Pending",
    approved: "Approved",
    rejected: "Rejected",
    posted: "Posted",
    all: "All",
};

const STATUS_COLORS: Record<string, string> = {
    PENDING: "bg-yellow/20 text-yellow",
    APPROVED: "bg-green/20 text-green",
    REJECTED: "bg-red/20 text-red",
    POSTED: "bg-green/40 text-green",
};

function Badge({status}: {status: string}) {
    return (
        <span
            className={`px-2.5 py-0.5 rounded-xl text-[0.7rem] font-semibold uppercase tracking-wide ${STATUS_COLORS[status] ?? ""}`}
        >
            {status}
        </span>
    );
}

export function Template(props: Props) {
    const {drafts, tab, counts, subreddit_configs, today_counts, weekly_counts} =
        props;

    return (
        <Shell>
            <div className="max-w-[900px] mx-auto px-4 py-6">
                <div className="flex justify-between items-start mb-2">
                    <h1 className="text-2xl font-semibold">
                        Reddit <span className="text-accent">Draft Queue</span>
                    </h1>
                    <a
                        href="/subreddits"
                        className="text-muted text-sm hover:text-text"
                    >
                        Subreddit Settings
                    </a>
                </div>
                <div className="text-muted text-sm mb-6">
                    Review AI-drafted replies before posting
                </div>

                <div className="flex gap-2 mb-6 flex-wrap">
                    {(
                        ["pending", "approved", "rejected", "posted", "all"] as const
                    ).map((t) => (
                        <a
                            key={t}
                            href={`?tab=${t}`}
                            className={`px-4 py-2 rounded-lg text-sm transition-all ${
                                tab === t
                                    ? "bg-accent2 text-text"
                                    : "bg-card text-muted hover:text-text"
                            }`}
                        >
                            {STATUS_LABELS[t]}
                            <span className="bg-white/10 px-1.5 py-0.5 rounded-xl text-xs ml-1">
                                {counts[t]}
                            </span>
                        </a>
                    ))}
                </div>

                {drafts.length > 0 ? (
                    drafts.map((d) => {
                        const subCfg = subreddit_configs[d.subreddit_name];
                        const preview = (
                            d.edited_reply || d.draft_reply
                        ).slice(0, 200);

                        return (
                            <a
                                key={d.id}
                                href={`/draft/${d.id}/`}
                                className="block bg-card rounded-xl p-5 mb-3 border border-transparent hover:border-accent2 hover:-translate-y-0.5 transition-all"
                            >
                                <div className="flex justify-between items-start mb-2">
                                    <span className="text-accent font-semibold text-sm">
                                        r/{d.subreddit_name}
                                        {subCfg?.banned && (
                                            <span className="bg-red/30 text-red px-2 py-0.5 rounded-lg text-[0.65rem] font-semibold ml-1.5">
                                                BANNED
                                            </span>
                                        )}
                                        {subCfg?.post_via ===
                                            "CROWDREPLY" && (
                                            <span className="bg-green/20 text-green px-2 py-0.5 rounded-lg text-[0.65rem] ml-1.5">
                                                via CrowdReply
                                            </span>
                                        )}
                                        {subCfg &&
                                            (today_counts[
                                                d.subreddit_name
                                            ] ?? 0) >=
                                                subCfg.daily_limit && (
                                                <span className="bg-yellow/20 text-yellow px-2 py-0.5 rounded-lg text-[0.65rem] ml-1.5">
                                                    DAY LIMIT
                                                </span>
                                            )}
                                        {subCfg &&
                                            (weekly_counts[
                                                d.subreddit_name
                                            ] ?? 0) >=
                                                subCfg.weekly_limit && (
                                                <span className="bg-yellow/20 text-yellow px-2 py-0.5 rounded-lg text-[0.65rem] ml-1.5">
                                                    WEEK LIMIT
                                                </span>
                                            )}
                                        {d.matched_keyword && (
                                            <span className="bg-purple-500/15 text-purple-400 px-2 py-0.5 rounded-lg text-[0.7rem] ml-1">
                                                {d.matched_keyword}
                                            </span>
                                        )}
                                    </span>
                                    <Badge status={d.status} />
                                </div>
                                <div className="text-base font-medium mb-1.5">
                                    {d.post_title}
                                </div>
                                <div className="text-muted text-sm leading-relaxed line-clamp-2">
                                    {preview}
                                </div>
                                <div className="text-muted text-xs mt-2">
                                    {d.post_author &&
                                        `by u/${d.post_author} \u00b7 `}
                                    {d.created_at.slice(0, 16)}
                                    {d.edited_reply &&
                                        d.edited_reply !==
                                            d.draft_reply && (
                                            <span className="text-green ml-2">
                                                edited
                                            </span>
                                        )}
                                    {d.edit_notes && (
                                        <span className="text-yellow ml-1">
                                            notes
                                        </span>
                                    )}
                                </div>
                            </a>
                        );
                    })
                ) : (
                    <div className="text-center py-16 text-muted">
                        <div className="text-4xl mb-3">No {tab} drafts yet</div>
                    </div>
                )}
            </div>
        </Shell>
    );
}
