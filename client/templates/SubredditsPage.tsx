import React from "react";

import {Shell} from "@client/components/Shell";
import * as schema from "@client/schema";
import {templates} from "@client/schema";

type Props = templates.SubredditsPage;

export function Template(props: Props) {
    const {subreddits} = props;

    const [name, setName] = React.useState("");
    const [banned, setBanned] = React.useState(false);
    const [postVia, setPostVia] = React.useState<schema.PostVia>("SELF");
    const [dailyLimit, setDailyLimit] = React.useState(3);
    const [weeklyLimit, setWeeklyLimit] = React.useState(10);
    const [competitors, setCompetitors] = React.useState("");
    const [notes, setNotes] = React.useState("");

    const handleSave = async () => {
        if (!name.trim()) return;
        await schema.save_subreddit({
            name: name.trim(),
            banned,
            post_via: postVia,
            daily_limit: dailyLimit,
            weekly_limit: weeklyLimit,
            competitors,
            notes,
        });
        window.location.reload();
    };

    const handleDelete = async (subName: string) => {
        if (!confirm(`Delete config for r/${subName}?`)) return;
        await schema.delete_subreddit({name: subName});
        window.location.reload();
    };

    return (
        <Shell title="Subreddit Settings \u2014 Reddit Draft Queue">
            <div className="max-w-[800px] mx-auto px-4 py-6">
                <a
                    href="/"
                    className="text-muted text-sm hover:text-text inline-block mb-4"
                >
                    &larr; Back to queue
                </a>
                <h1 className="text-2xl font-semibold mb-1">
                    Subreddit{" "}
                    <span className="text-accent">Settings</span>
                </h1>
                <div className="text-muted text-sm mb-6">
                    Ban status, posting method, and daily rate limits
                </div>

                {subreddits.length > 0 ? (
                    <div className="bg-card rounded-xl p-5 mb-6 overflow-x-auto">
                        <table className="w-full border-collapse">
                            <thead>
                                <tr>
                                    {[
                                        "Subreddit",
                                        "Status",
                                        "Post via",
                                        "Limits",
                                        "Usage",
                                        "Competitors",
                                        "Notes",
                                        "",
                                    ].map((h) => (
                                        <th
                                            key={h}
                                            className="text-left text-muted text-[0.7rem] uppercase tracking-wider px-3 py-2 border-b border-white/5"
                                        >
                                            {h}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {subreddits.map((s) => (
                                    <tr
                                        key={s.name}
                                        className="border-b border-white/[0.03]"
                                    >
                                        <td className="px-3 py-2.5 text-sm">
                                            <a
                                                href={`https://www.reddit.com/r/${s.name}/`}
                                                target="_blank"
                                                rel="noreferrer"
                                                className="text-accent font-semibold no-underline"
                                            >
                                                r/{s.name}
                                            </a>
                                        </td>
                                        <td className="px-3 py-2.5 text-sm">
                                            {s.banned ? (
                                                <span className="text-red">
                                                    Banned
                                                </span>
                                            ) : (
                                                <span className="text-green">
                                                    OK
                                                </span>
                                            )}
                                        </td>
                                        <td className="px-3 py-2.5 text-sm">
                                            {s.post_via === "CROWDREPLY" ? (
                                                <span className="text-yellow text-sm">
                                                    CrowdReply
                                                </span>
                                            ) : (
                                                <span className="text-green text-sm">
                                                    Self
                                                </span>
                                            )}
                                        </td>
                                        <td className="px-3 py-2.5 text-sm">
                                            {s.daily_limit}/day &middot;{" "}
                                            {s.weekly_limit}/wk
                                        </td>
                                        <td className="px-3 py-2.5 text-sm">
                                            <UsageDisplay
                                                used={s.today_used}
                                                limit={s.daily_limit}
                                                suffix="d"
                                            />{" "}
                                            &middot;{" "}
                                            <UsageDisplay
                                                used={s.weekly_used}
                                                limit={s.weekly_limit}
                                                suffix="w"
                                            />
                                        </td>
                                        <td
                                            className="px-3 py-2.5 text-sm text-muted"
                                            title={s.competitors}
                                        >
                                            {s.competitors
                                                ? s.competitors.slice(0, 40) +
                                                  (s.competitors.length > 40
                                                      ? "\u2026"
                                                      : "")
                                                : "\u2014"}
                                        </td>
                                        <td className="px-3 py-2.5 text-sm text-muted">
                                            {s.notes || "\u2014"}
                                        </td>
                                        <td className="px-3 py-2.5">
                                            <button
                                                onClick={() =>
                                                    handleDelete(s.name)
                                                }
                                                className="px-2.5 py-1 rounded-md text-xs bg-red/20 text-red hover:bg-red/40 cursor-pointer"
                                            >
                                                x
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <div className="text-center py-10 text-muted">
                        No subreddits configured yet. Add one below.
                    </div>
                )}

                {/* Add / Update form */}
                <div className="bg-card rounded-xl p-6">
                    <h2 className="text-xs uppercase tracking-widest text-muted mb-4">
                        Add / Update Subreddit
                    </h2>
                    <div className="flex gap-3 mb-3 flex-wrap items-center">
                        <input
                            type="text"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            placeholder="Subreddit name (no r/)"
                            className="bg-bg text-text border border-accent2 rounded-lg px-3 py-2 text-sm w-44 focus:outline-none focus:border-accent"
                        />
                        <label className="flex items-center gap-1.5 text-sm text-muted cursor-pointer">
                            <input
                                type="checkbox"
                                checked={banned}
                                onChange={(e) => setBanned(e.target.checked)}
                                className="accent-accent"
                            />
                            Banned from main
                        </label>
                    </div>
                    <div className="flex gap-3 mb-3 flex-wrap items-center">
                        <label className="text-sm text-muted">
                            Post via:
                            <select
                                value={postVia}
                                onChange={(e) => setPostVia(e.target.value as schema.PostVia)}
                                className="bg-bg text-text border border-accent2 rounded-lg px-3 py-2 text-sm ml-2 w-44 focus:outline-none focus:border-accent"
                            >
                                <option value="SELF">Self</option>
                                <option value="CROWDREPLY">CrowdReply</option>
                            </select>
                        </label>
                        <label className="text-sm text-muted">
                            Daily:
                            <input
                                type="number"
                                value={dailyLimit}
                                onChange={(e) =>
                                    setDailyLimit(Number(e.target.value))
                                }
                                min={0}
                                max={50}
                                className="bg-bg text-text border border-accent2 rounded-lg px-3 py-2 text-sm ml-2 w-20 focus:outline-none focus:border-accent"
                            />
                        </label>
                        <label className="text-sm text-muted">
                            Weekly:
                            <input
                                type="number"
                                value={weeklyLimit}
                                onChange={(e) =>
                                    setWeeklyLimit(Number(e.target.value))
                                }
                                min={0}
                                max={100}
                                className="bg-bg text-text border border-accent2 rounded-lg px-3 py-2 text-sm ml-2 w-20 focus:outline-none focus:border-accent"
                            />
                        </label>
                    </div>
                    <div className="mb-3">
                        <textarea
                            value={competitors}
                            onChange={(e) => setCompetitors(e.target.value)}
                            placeholder="Competitors to mention (one per line)"
                            className="w-full max-w-md bg-bg text-text border border-accent2 rounded-lg px-3 py-2 text-sm resize-y min-h-[60px] font-sans focus:outline-none focus:border-accent"
                        />
                    </div>
                    <div className="mb-3">
                        <input
                            type="text"
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                            placeholder="Notes (optional)"
                            className="w-full max-w-md bg-bg text-text border border-accent2 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent"
                        />
                    </div>
                    <button
                        onClick={handleSave}
                        className="px-4 py-2 rounded-lg text-sm font-semibold bg-accent2 text-text hover:-translate-y-0.5 transition-all cursor-pointer"
                    >
                        Save
                    </button>
                </div>
            </div>
        </Shell>
    );
}

function UsageDisplay({
    used,
    limit,
    suffix,
}: {
    used: number;
    limit: number;
    suffix: string;
}) {
    let color = "text-green";
    if (used >= limit) color = "text-red";
    else if (used > 0) color = "text-yellow";

    return (
        <span className={color}>
            {used}/{limit}
            {suffix}
        </span>
    );
}
