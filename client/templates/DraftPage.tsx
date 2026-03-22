import React from "react";

import {Shell} from "@client/components/Shell";
import * as schema from "@client/schema";
import {templates} from "@client/schema";

type Props = templates.DraftPage;

const STATUS_COLORS: Record<string, string> = {
    PENDING: "bg-yellow/20 text-yellow",
    APPROVED: "bg-green/20 text-green",
    REJECTED: "bg-red/20 text-red",
    POSTED: "bg-green/40 text-green",
};

export function Template(props: Props) {
    const {draft, sub_info, today_count} = props;

    const [editedReply, setEditedReply] = React.useState(
        draft.edited_reply || draft.draft_reply,
    );
    const [editNotes, setEditNotes] = React.useState(draft.edit_notes);
    const [notes, setNotes] = React.useState(draft.notes);
    const [buyUpvotes, setBuyUpvotes] = React.useState(draft.buy_upvotes);
    const [draftReply, setDraftReply] = React.useState(draft.draft_reply);

    const handleStatusChange = async (newStatus: schema.Status) => {
        await schema.update_draft_status({
            draft_id: draft.id,
            status: newStatus,
            edited_reply: editedReply,
            edit_notes: editNotes,
            buy_upvotes: buyUpvotes,
        });
        window.location.href = "/";
    };

    const handleSaveEdits = async () => {
        await schema.save_draft_edits({
            draft_id: draft.id,
            draft_reply: draftReply,
            edited_reply: editedReply,
            edit_notes: editNotes,
            notes,
            buy_upvotes: buyUpvotes,
        });
        window.location.href = `/draft/${draft.id}/`;
    };

    return (
        <Shell title={`Draft #${draft.id} \u2014 Reddit Draft Queue`}>
            <div className="max-w-[800px] mx-auto px-4 py-6">
                <a
                    href="/"
                    className="text-muted text-sm hover:text-text inline-block mb-4"
                >
                    &larr; Back to queue
                </a>

                {/* Original Post */}
                <div className="bg-card rounded-xl p-6 mb-4">
                    <h2 className="text-xs uppercase tracking-widest text-muted mb-3">
                        Original Post
                    </h2>
                    <div className="text-accent font-semibold text-sm mb-1">
                        r/{draft.subreddit_name}
                        {sub_info?.banned && (
                            <span className="bg-red/30 text-red px-2 py-0.5 rounded-lg text-[0.65rem] font-semibold ml-1.5">
                                BANNED &mdash; post via{" "}
                                {sub_info.post_via === "CROWDREPLY"
                                    ? "CrowdReply"
                                    : "Self"}
                            </span>
                        )}
                        {sub_info &&
                            today_count >= sub_info.daily_limit && (
                                <span className="bg-yellow/30 text-yellow px-2 py-0.5 rounded-lg text-[0.65rem] font-semibold ml-1.5">
                                    DAILY LIMIT ({today_count}/
                                    {sub_info.daily_limit})
                                </span>
                            )}
                        {sub_info?.competitors && (
                            <div className="mt-2 text-sm text-muted">
                                Mention: {sub_info.competitors}
                            </div>
                        )}
                    </div>
                    <div className="text-xl font-semibold mb-2">
                        <a
                            href={draft.post_url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-text hover:underline"
                        >
                            {draft.post_title}
                        </a>
                    </div>
                    <div className="text-muted text-sm mb-3">
                        {draft.post_author &&
                            `by u/${draft.post_author} \u00b7 `}
                        {draft.created_at.slice(0, 16)}
                    </div>
                    {draft.post_body && (
                        <div className="text-muted text-sm leading-relaxed whitespace-pre-wrap max-h-72 overflow-y-auto">
                            {draft.post_body}
                        </div>
                    )}
                </div>

                {/* Draft Reply */}
                <div className="bg-card rounded-xl p-6 mb-4">
                    <h2 className="text-xs uppercase tracking-widest text-muted mb-3">
                        Draft Reply
                    </h2>
                    <span
                        className={`px-3 py-1 rounded-xl text-xs font-semibold uppercase inline-block mb-3 ${STATUS_COLORS[draft.status] ?? ""}`}
                    >
                        {draft.status}
                    </span>
                    {draft.matched_keyword && (
                        <span className="bg-purple-500/15 text-purple-400 px-3 py-1 rounded-xl text-xs ml-2">
                            {draft.matched_keyword}
                        </span>
                    )}

                    {/* Original Draft (read-only) */}
                    <h2 className="text-xs uppercase tracking-widest text-muted mb-3 mt-4">
                        Original Draft{" "}
                        <span className="text-[0.65rem] text-muted normal-case tracking-normal">
                            (do not edit &mdash; this is the AI original)
                        </span>
                    </h2>
                    <textarea
                        value={draftReply}
                        readOnly
                        className="w-full bg-black/30 text-text border border-accent2 rounded-lg p-3 font-sans text-sm leading-relaxed resize-y min-h-[150px] opacity-60"
                    />

                    {/* Edited Version */}
                    <h2 className="text-xs uppercase tracking-widest text-muted mb-3 mt-4">
                        Edited Version{" "}
                        <span className="text-[0.65rem] text-green normal-case tracking-normal">
                            (this gets published)
                        </span>
                    </h2>
                    <textarea
                        value={editedReply}
                        onChange={(e) => setEditedReply(e.target.value)}
                        className="w-full bg-bg text-text border border-accent2 rounded-lg p-3 font-sans text-sm leading-relaxed resize-y min-h-[150px] focus:outline-none focus:border-accent"
                    />

                    {/* Buy upvotes */}
                    <div className="mt-4 flex items-center gap-2">
                        <label className="flex items-center gap-2 cursor-pointer">
                            <input
                                type="checkbox"
                                checked={buyUpvotes}
                                onChange={(e) =>
                                    setBuyUpvotes(e.target.checked)
                                }
                                className="w-[18px] h-[18px] accent-green"
                            />
                            <span className="text-sm font-semibold">
                                Buy upvotes after posting
                            </span>
                        </label>
                        {draft.upvotes_needed != null && (
                            <span className="text-xs text-muted">
                                ({draft.upvotes_needed} needed to beat top
                                comment)
                            </span>
                        )}
                    </div>

                    {/* Edit notes */}
                    <h2 className="text-xs uppercase tracking-widest text-muted mb-3 mt-4">
                        Edit Notes{" "}
                        <span className="text-[0.65rem] text-muted normal-case tracking-normal">
                            (optional &mdash; explain what you changed and why)
                        </span>
                    </h2>
                    <textarea
                        value={editNotes}
                        onChange={(e) => setEditNotes(e.target.value)}
                        placeholder="e.g. 'Toned down the opener, added specific dose mention, removed generic link...'"
                        className="w-full bg-bg text-text border border-accent2 rounded-lg p-3 font-sans text-sm leading-relaxed resize-y min-h-[60px] focus:outline-none focus:border-accent"
                    />

                    {/* Internal notes */}
                    <h2 className="text-xs uppercase tracking-widest text-muted mb-3 mt-4">
                        Internal Notes
                    </h2>
                    <textarea
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        placeholder="Internal notes..."
                        className="w-full bg-bg text-text border border-accent2 rounded-lg p-3 font-sans text-sm leading-relaxed resize-y min-h-[60px] focus:outline-none focus:border-accent"
                    />

                    {/* Save button */}
                    <div className="flex gap-2 mt-4">
                        <button
                            onClick={handleSaveEdits}
                            className="px-5 py-2.5 rounded-lg text-sm font-semibold bg-accent2 text-text hover:-translate-y-0.5 transition-all cursor-pointer"
                        >
                            Save Edits
                        </button>
                    </div>

                    {/* Status buttons */}
                    <div className="flex gap-2 mt-3">
                        <button
                            onClick={() => handleStatusChange("APPROVED")}
                            className="px-5 py-2.5 rounded-lg text-sm font-semibold bg-green text-[#111] hover:-translate-y-0.5 transition-all cursor-pointer"
                        >
                            Approve
                        </button>
                        <button
                            onClick={() => handleStatusChange("REJECTED")}
                            className="px-5 py-2.5 rounded-lg text-sm font-semibold bg-red text-white hover:-translate-y-0.5 transition-all cursor-pointer"
                        >
                            Reject
                        </button>
                        <button
                            onClick={() => handleStatusChange("PENDING")}
                            className="px-5 py-2.5 rounded-lg text-sm font-semibold bg-yellow text-[#111] hover:-translate-y-0.5 transition-all cursor-pointer"
                        >
                            Back to Pending
                        </button>
                    </div>
                </div>

                {draft.reviewed_at && (
                    <div className="text-center text-muted text-sm">
                        Reviewed: {draft.reviewed_at.slice(0, 16)}
                    </div>
                )}
            </div>
        </Shell>
    );
}
