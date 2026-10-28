import { Badge } from "@astryxdesign/core/Badge";
import { Button } from "@astryxdesign/core/Button";
import { Card } from "@astryxdesign/core/Card";
import { EmptyState } from "@astryxdesign/core/EmptyState";
import { TextInput } from "@astryxdesign/core/TextInput";
import {
  CheckCircle2,
  CheckSquare,
  Clock,
  FileSearch,
  ListPlus,
  Music2,
  RefreshCw,
  Search,
  Sparkles,
  Square,
  Trash2
} from "lucide-react";
import React, { useMemo, useState } from "react";
import { getServiceInfo } from "../lib/catalogServices";
import {
  DownloadProfile,
  ParsingJob,
  PendingQueueItem
} from "../types";
import { PageHeader } from "./PageHeader";

interface ParsingPendingQueueProps {
  jobs: ParsingJob[];
  pendingItems: PendingQueueItem[];
  profiles: DownloadProfile[];
  activeProfile: string;
  onChangeActiveProfile: (profileId: string) => Promise<void>;
  onParseUrl: (url: string, profileId?: string, autoQueue?: boolean) => Promise<boolean>;
  onCancelJob: (jobId: string) => Promise<void>;
  onDeleteJob: (jobId: string) => Promise<void>;
  onClearCompletedJobs: () => Promise<void>;
  onQueuePendingItems: (itemIds: string[], profileId?: string) => Promise<void>;
  onRemovePendingItems: (itemIds: string[]) => Promise<void>;
  onClearAllPending: () => Promise<void>;
  onRefresh?: () => Promise<void>;
}

export const ParsingPendingQueue: React.FC<ParsingPendingQueueProps> = ({
  jobs,
  pendingItems,
  profiles,
  activeProfile,
  onChangeActiveProfile,
  onParseUrl,
  onCancelJob,
  onDeleteJob,
  onClearCompletedJobs,
  onQueuePendingItems,
  onRemovePendingItems,
  onClearAllPending,
  onRefresh,
}) => {
  const [inputUrl, setInputUrl] = useState("");
  const [selectedProfileId, setSelectedProfileId] = useState(activeProfile || "");
  const [autoQueueOnParsed, setAutoQueueOnParsed] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [searchFilter, setSearchFilter] = useState("");
  const [selectedService, setSelectedService] = useState<string>("all");
  const [selectedStatus, setSelectedStatus] = useState<string>("all");
  const [selectedItemIds, setSelectedItemIds] = useState<Set<string>>(new Set());
  const [jobFilterId, setJobFilterId] = useState<string | null>(null);



  const handleParseSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputUrl.trim()) return;

    setIsSubmitting(true);
    try {
      const accepted = await onParseUrl(inputUrl.trim(), selectedProfileId, autoQueueOnParsed);
      if (accepted) setInputUrl("");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleApplyPreset = (url: string) => {
    setInputUrl(url);
  };

  // Filter pending items
  const filteredPendingItems = useMemo(() => {
    return pendingItems.filter((item) => {
      if (jobFilterId && item.job_id !== jobFilterId) return false;
      if (selectedService !== "all" && item.item_service !== selectedService) return false;
      if (selectedStatus !== "all" && item.status !== selectedStatus) return false;

      if (searchFilter.trim()) {
        const q = searchFilter.toLowerCase();
        const matchTitle = item.name.toLowerCase().includes(q);
        const matchArtist = item.artist.toLowerCase().includes(q);
        const matchAlbum = item.album ? item.album.toLowerCase().includes(q) : false;
        const matchPlaylist = item.playlist_name ? item.playlist_name.toLowerCase().includes(q) : false;
        if (!matchTitle && !matchArtist && !matchAlbum && !matchPlaylist) return false;
      }
      return true;
    });
  }, [pendingItems, jobFilterId, selectedService, selectedStatus, searchFilter]);

  const visibleJobs = useMemo(() => {
    return jobs.filter((j) => j.status === "parsing" || j.status === "failed");
  }, [jobs]);

  // Selection handlers
  const allFilteredSelected =
    filteredPendingItems.length > 0 &&
    filteredPendingItems.every((item) => selectedItemIds.has(item.id));

  const toggleSelectAll = () => {
    if (allFilteredSelected) {
      setSelectedItemIds(new Set());
    } else {
      setSelectedItemIds(new Set(filteredPendingItems.map((i) => i.id)));
    }
  };

  const toggleSelectItem = (id: string) => {
    setSelectedItemIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleRemoveSelected = async () => {
    const ids = Array.from(selectedItemIds);
    if (ids.length === 0) return;
    await onRemovePendingItems(ids);
    setSelectedItemIds(new Set());
  };

  const handleProfileChange = async (profileId: string) => {
    onChangeActiveProfile(profileId)
    setSelectedProfileId(profileId)
  }
  const readyItemsCount = pendingItems.filter((i) => i.status === "ready").length;
  const parsingItemsCount = pendingItems.filter((i) => i.status === "parsing").length;
  const activeJobsCount = visibleJobs.filter((j) => j.status === "parsing").length;

  return (
    <div className="space-y-5" id="parsing-pending-queue-view">
      {/* Page Header */}
      <PageHeader
        id="parsing-queue-header"
        icon={<ListPlus className="w-5 h-5 text-amber-500" />}
        title="Parsing & Pending Queue"
        badge={{
          label: `${pendingItems.length} Staged Items`,
          variant: pendingItems.length > 0 ? "info" : "neutral",
        }}
        description="Inspect media link scraping jobs, review resolved metadata, and batch queue tracks for background downloading."
        actions={
          <div className="flex items-center gap-2 flex-wrap">
            {onRefresh && (
              <Button
                variant="secondary"
                size="sm"
                label="Refresh"
                icon={<RefreshCw className="w-3.5 h-3.5" />}
                onClick={onRefresh}
                id="btn-refresh-parsing"
              />
            )}
            {jobs.some((j) => j.status === "completed" || j.status === "failed") && (
              <Button
                variant="secondary"
                size="sm"
                label="Clear Finished Jobs"
                icon={<CheckCircle2 className="w-3.5 h-3.5 text-neutral-400" />}
                onClick={onClearCompletedJobs}
                id="btn-clear-jobs"
              />
            )}
          </div>
        }
      />

      {/* Parse URL Input Card */}
      <Card padding={4} elevation="low" id="parse-url-input-card">
        <form onSubmit={handleParseSubmit} className="space-y-4">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber-500" />
              <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                Parse Media Link or Batch Playlist
              </h3>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-neutral-500">Target Profile:</span>
              <select
                value={selectedProfileId}
                onChange={(e) => handleProfileChange(e.target.value)}
                className="text-xs font-medium px-2 py-1 rounded bg-neutral-100 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 text-neutral-800 dark:text-neutral-200 focus:outline-hidden"
              >
                {profiles.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.format} {p.bitrate})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center">
            <div className="flex-1">
              <TextInput
                label="Media URL to parse"
                isLabelHidden={true}
                placeholder="Paste Spotify, Deezer, Tidal, Apple Music, YouTube album, playlist, or track URL..."
                value={inputUrl}
                onChange={(val) => setInputUrl(val)}
                hasClear={true}
                size="md"
                startIcon={<FileSearch className="w-4 h-4 text-neutral-400" />}
              />
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <Button
                type="submit"
                variant="primary"
                size="md"
                label={isSubmitting ? "Submitting..." : "Start Parsing"}
                icon={<Sparkles className="w-4 h-4" />}
                isDisabled={!inputUrl.trim() || isSubmitting}
                id="btn-submit-parse-url"
              />
            </div>
          </div>


        </form>
      </Card>

  

      {/* Pending Items Management Card */}
      <Card padding={4} elevation="low" id="pending-items-card">
        {/* Filter and Batch Toolbar */}
        <div className="space-y-3">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                Staged Tracks Awaiting Downloader
              </h3>
              <Badge variant="neutral" label={`${filteredPendingItems.length} tracks`} />
              {jobFilterId && (
                <Badge
                  variant="warning"
                  label="Filtered by Job"
                />
              )}
            </div>

            {/* Quick Batch Actions */}
            <div className="flex items-center gap-2 flex-wrap">
              {selectedItemIds.size > 0 && (
                <>
                  <span className="text-xs font-mono text-neutral-500">
                    {selectedItemIds.size} selected
                  </span>
                  <Button
                    variant="secondary"
                    size="sm"
                    label="Remove"
                    icon={<Trash2 className="w-3.5 h-3.5 text-neutral-400" />}
                    onClick={handleRemoveSelected}
                    id="btn-remove-selected"
                  />
                </>
              )}
              {pendingItems.length > 0 && selectedItemIds.size === 0 && (
                <Button
                  variant="secondary"
                  size="sm"
                  label="Clear Staged List"
                  icon={<Trash2 className="w-3.5 h-3.5 text-neutral-400" />}
                  onClick={onClearAllPending}
                  id="btn-clear-all-pending"
                />
              )}
            </div>
          </div>

          {/* Search and Filters Bar */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 pt-2 border-t border-neutral-100 dark:border-neutral-800">
            <div className="flex-1">
              <TextInput
                label="Filter pending tracks"
                isLabelHidden={true}
                placeholder="Filter by track, artist, album, or playlist..."
                value={searchFilter}
                onChange={(val) => setSearchFilter(val)}
                hasClear={true}
                size="sm"
                startIcon={<Search className="w-3.5 h-3.5 text-neutral-400" />}
              />
            </div>

            {/* Service Filter Chips */}
            <div className="flex items-center gap-1 overflow-x-auto text-xs py-0.5">
              {(["all", "spotify", "deezer", "tidal", "youtube"] as const).map((svc) => (
                <button
                  key={svc}
                  type="button"
                  onClick={() => setSelectedService(svc)}
                  className={`px-2.5 py-1 rounded-md text-[11px] font-medium capitalize transition cursor-pointer shrink-0 ${
                    selectedService === svc
                      ? "bg-neutral-900 dark:bg-neutral-100 text-white dark:text-neutral-900"
                      : "bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300 hover:bg-neutral-200"
                  }`}
                >
                  {svc}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Live Auto-Queue Ingestion Banner */}
        {pendingItems.length > 0 && (
          <div className="mt-4 p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200/50 dark:border-emerald-800/30 flex items-center gap-2.5 text-xs text-emerald-800 dark:text-emerald-300">
            <Clock className="w-4 h-4 text-emerald-500 shrink-0 animate-pulse" />
            <div className="min-w-0 flex-1">
              <span className="font-semibold">Automatic Ingestion Active:</span> Staged tracks are automatically parsed and digested by the background download worker once metadata is fully resolved. No manual queuing is required.
            </div>
          </div>
        )}

        {/* Pending Items List */}
        <div className="mt-4">
          {filteredPendingItems.length < 1 ? (
            <div className="py-12 text-center">
              <EmptyState
                icon={<Clock className="w-8 h-8 text-neutral-400" />}
                title="No Pending Items Found"
                description={
                  searchFilter || selectedService !== "all" || selectedStatus !== "all"
                    ? "Try adjusting your search or filters above to see more tracks."
                    : "Paste a Spotify, Deezer, Tidal, or YouTube URL above to parse audio tracks into the staging queue."
                }
              />
            </div>
          ) : (
            <div className="space-y-2">
              {/* Table Column Header / Select All Bar */}
              <div className="flex items-center justify-between px-3 py-2 bg-neutral-100/70 dark:bg-neutral-800/50 rounded-lg text-xs font-semibold text-neutral-500">
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={toggleSelectAll}
                    className="cursor-pointer text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200"
                    title={allFilteredSelected ? "Deselect All" : "Select All"}
                  >
                    {allFilteredSelected ? (
                      <CheckSquare className="w-4 h-4 text-emerald-500" />
                    ) : (
                      <Square className="w-4 h-4" />
                    )}
                  </button>
                  <span>Track & Artist</span>
                </div>
                <div className="flex items-center gap-6">
                  <span className="hidden md:inline">Source & Profile</span>
                  <span className="hidden sm:inline">Status</span>
                  <span>Action</span>
                </div>
              </div>

              {/* Item Rows */}
              {filteredPendingItems.map((item) => {
                const svcInfo = getServiceInfo(item.item_service);
                const isSelected = selectedItemIds.has(item.id);
                const isReady = item.status === "ready";

                return (
                  <div
                    key={item.id}
                    className={`flex items-center justify-between gap-3 p-2.5 rounded-lg border transition ${
                      isSelected
                        ? "bg-amber-50/40 dark:bg-amber-950/20 border-amber-500/40"
                        : "bg-white dark:bg-neutral-900/40 border-neutral-200/80 dark:border-neutral-800 hover:border-neutral-300 dark:hover:border-neutral-700"
                    }`}
                    id={`pending-row-${item.id}`}
                  >
                    {/* Left details */}
                    <div className="flex items-center gap-3 min-w-0 flex-1">
                      <button
                        type="button"
                        onClick={() => toggleSelectItem(item.id)}
                        className="cursor-pointer text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 shrink-0"
                      >
                        {isSelected ? (
                          <CheckSquare className="w-4 h-4 text-amber-500" />
                        ) : (
                          <Square className="w-4 h-4" />
                        )}
                      </button>

                      {/* Thumbnail with service dot */}
                      <div className="relative w-10 h-10 rounded-md overflow-hidden bg-neutral-200 dark:bg-neutral-800 shrink-0 shadow-xs">
                        {item.thumbnail ? (
                          <img
                            src={item.thumbnail}
                            alt={item.name}
                            className="w-full h-full object-cover"
                            referrerPolicy="no-referrer"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-neutral-400">
                            <Music2 className="w-4 h-4" />
                          </div>
                        )}
                        <span
                          className="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-tl-sm"
                          style={{ backgroundColor: svcInfo.color }}
                          title={`Source: ${svcInfo.name}`}
                        />
                      </div>

                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1.5 truncate">
                          <span className="font-semibold text-xs text-neutral-900 dark:text-neutral-100 truncate">
                            {item.name}
                          </span>
                          {item.explicit && (
                            <span className="text-[10px] px-1 py-0.2 rounded bg-neutral-200 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-300 font-bold uppercase shrink-0">
                              E
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-1.5 text-[11px] text-neutral-500 truncate mt-0.5">
                          <span className="truncate">{item.artist}</span>
                          {item.album && (
                            <>
                              <span>•</span>
                              <span className="truncate text-neutral-400">{item.album}</span>
                            </>
                          )}
                          {item.duration && (
                            <>
                              <span>•</span>
                              <span className="font-mono text-neutral-400">{item.duration}</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Right specs & actions */}
                    <div className="flex items-center gap-3 shrink-0">
                      {/* Technical specifications */}
                      <div className="hidden md:flex items-center gap-1.5">
                        <span
                          className="text-[10px] font-semibold px-2 py-0.5 rounded uppercase tracking-wider"
                          style={{
                            backgroundColor: `${svcInfo.color}15`,
                            color: svcInfo.color,
                          }}
                        >
                          {svcInfo.name}
                        </span>
                        <Badge
                          variant="neutral"
                          label={`${item.format || "FLAC"} • ${item.bitrate || "Lossless"}`}
                        />
                      </div>

                      {/* Status indicator */}
                      <div className="hidden sm:block">
                        {item.status === "ready" ? (
                          <Badge variant="success" label="Ready" />
                        ) : item.status === "parsing" ? (
                          <Badge variant="warning" label="Resolving..." />
                        ) : (
                          <Badge variant="error" label="Error" />
                        )}
                      </div>

                      {/* Action buttons */}
                      <div className="flex items-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => onRemovePendingItems([item.id])}
                          className="p-1.5 rounded-md text-neutral-400 hover:text-red-500 dark:hover:text-red-400 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition cursor-pointer"
                          title="Remove item"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </Card>
    </div>
  );
};
