import React, { useState } from "react";
import {
  ClipboardList,
  Search,
  Plus,
  Play,
  CheckCircle,
  RotateCcw,
  AlertTriangle,
  AlertCircle,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import type {
  MaintenanceTask,
  MaintenanceTaskCategory,
  MaintenanceTaskCreateRequest,
  MaintenanceTaskPriority,
  MaintenanceTaskStatus,
  TaskCancelRequest,
  TaskCompleteRequest,
  TaskReopenRequest,
} from "@/types/monitoring";
import type { Project } from "@/types/projects";
import type { UserProfile } from "@/types/auth";

interface MaintenanceTasksTabProps {
  tasks: MaintenanceTask[];
  projects: Project[];
  users: UserProfile[];
  currentUserId?: string;
  currentUserRole?: string;
  selectedProjectId?: string;
  onCreateTask: (data: MaintenanceTaskCreateRequest) => Promise<any>;
  onStartTask: (id: string) => Promise<any>;
  onCompleteTask: (id: string, data: TaskCompleteRequest) => Promise<any>;
  onCancelTask: (id: string, data: TaskCancelRequest) => Promise<any>;
  onReopenTask: (id: string, data: TaskReopenRequest) => Promise<any>;
}

export const MaintenanceTasksTab: React.FC<MaintenanceTasksTabProps> = ({
  tasks,
  projects,
  users,
  currentUserId,
  currentUserRole,
  selectedProjectId,
  onCreateTask,
  onStartTask,
  onCompleteTask,
  onCancelTask,
  onReopenTask,
}) => {
  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [priorityFilter, setPriorityFilter] = useState<string>("ALL");
  const [categoryFilter, setCategoryFilter] = useState<string>("ALL");

  // Modals
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isCompleteModalOpen, setIsCompleteModalOpen] = useState(false);
  const [isCancelModalOpen, setIsCancelModalOpen] = useState(false);
  const [isReopenModalOpen, setIsReopenModalOpen] = useState(false);
  const [activeTask, setActiveTask] = useState<MaintenanceTask | null>(null);

  // Form: Create Task
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState<MaintenanceTaskCategory>("IRRIGATION");
  const [priority, setPriority] = useState<MaintenanceTaskPriority>("MEDIUM");
  const [dueDate, setDueDate] = useState(
    new Date(Date.now() + 7 * 86400000).toISOString().split("T")[0]
  );
  const [assigneeId, setAssigneeId] = useState("");
  const [taskProjectId, setTaskProjectId] = useState(selectedProjectId || "");
  const [createError, setCreateError] = useState<string | null>(null);
  const [isSubmittingCreate, setIsSubmittingCreate] = useState(false);

  // Form: Complete Task
  const [completionNotes, setCompletionNotes] = useState("");
  const [completeError, setCompleteError] = useState<string | null>(null);

  // Form: Cancel Task
  const [cancellationReason, setCancellationReason] = useState("");
  const [cancelError, setCancelError] = useState<string | null>(null);

  // Form: Reopen Task
  const [justification, setJustification] = useState("");
  const [reopenError, setReopenError] = useState<string | null>(null);

  const canManage = currentUserRole === "ADMIN" || currentUserRole === "PROJECT_MANAGER";
  const todayStr = new Date().toISOString().split("T")[0];

  const getProjectName = (projId: string) => {
    return projects.find((p) => p.id === projId)?.name || "Assigned Project";
  };

  const getUserName = (userId?: string | null) => {
    if (!userId) return "Unassigned";
    const u = users.find((usr) => usr.id === userId);
    return u?.full_name || "Field Personnel";
  };

  // Filter tasks
  const filteredTasks = tasks.filter((t) => {
    if (statusFilter !== "ALL" && t.status !== statusFilter) return false;
    if (priorityFilter !== "ALL" && t.priority !== priorityFilter) return false;
    if (categoryFilter !== "ALL" && t.category !== categoryFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchTitle = t.title.toLowerCase().includes(q);
      const matchDesc = t.description?.toLowerCase().includes(q);
      if (!matchTitle && !matchDesc) return false;
    }
    return true;
  });

  const handleOpenCreateModal = () => {
    setTaskProjectId(selectedProjectId || projects[0]?.id || "");
    setTitle("");
    setDescription("");
    setCategory("IRRIGATION");
    setPriority("MEDIUM");
    setDueDate(new Date(Date.now() + 7 * 86400000).toISOString().split("T")[0]);
    setAssigneeId("");
    setCreateError(null);
    setIsCreateModalOpen(true);
  };

  const handleSubmitCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!taskProjectId) {
      setCreateError("Please select a target project.");
      return;
    }
    if (title.trim().length < 3) {
      setCreateError("Task title must be at least 3 characters.");
      return;
    }
    if (!dueDate) {
      setCreateError("Due date is required.");
      return;
    }

    try {
      setIsSubmittingCreate(true);
      setCreateError(null);
      await onCreateTask({
        project_id: taskProjectId,
        title: title.trim(),
        description: description.trim() || undefined,
        category,
        priority,
        due_date: dueDate,
        assigned_to_id: assigneeId || undefined,
      });
      setIsCreateModalOpen(false);
    } catch (err: any) {
      setCreateError(err?.message || "Failed to create maintenance task.");
    } finally {
      setIsSubmittingCreate(false);
    }
  };

  const handleOpenCompleteModal = (task: MaintenanceTask) => {
    setActiveTask(task);
    setCompletionNotes("");
    setCompleteError(null);
    setIsCompleteModalOpen(true);
  };

  const handleSubmitComplete = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeTask) return;
    if (completionNotes.trim().length < 3) {
      setCompleteError("Completion notes must be at least 3 characters.");
      return;
    }

    try {
      await onCompleteTask(activeTask.id, {
        completion_notes: completionNotes.trim(),
      });
      setIsCompleteModalOpen(false);
      setActiveTask(null);
    } catch (err: any) {
      setCompleteError(err?.message || "Failed to complete task.");
    }
  };

  const handleOpenCancelModal = (task: MaintenanceTask) => {
    setActiveTask(task);
    setCancellationReason("");
    setCancelError(null);
    setIsCancelModalOpen(true);
  };

  const handleSubmitCancel = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeTask) return;
    if (cancellationReason.trim().length < 3) {
      setCancelError("Cancellation reason must be at least 3 characters.");
      return;
    }

    try {
      await onCancelTask(activeTask.id, {
        cancellation_reason: cancellationReason.trim(),
      });
      setIsCancelModalOpen(false);
      setActiveTask(null);
    } catch (err: any) {
      setCancelError(err?.message || "Failed to cancel task.");
    }
  };

  const handleOpenReopenModal = (task: MaintenanceTask) => {
    setActiveTask(task);
    setJustification("");
    setReopenError(null);
    setIsReopenModalOpen(true);
  };

  const handleSubmitReopen = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeTask) return;
    if (justification.trim().length < 3) {
      setReopenError("Reopening justification must be at least 3 characters.");
      return;
    }

    try {
      await onReopenTask(activeTask.id, {
        justification: justification.trim(),
      });
      setIsReopenModalOpen(false);
      setActiveTask(null);
    } catch (err: any) {
      setReopenError(err?.message || "Failed to reopen task.");
    }
  };

  const getPriorityBadge = (p: MaintenanceTaskPriority, isOverdue: boolean) => {
    if (isOverdue) {
      return (
        <Badge variant="rejected" className="text-[10px] px-1.5 py-0 flex items-center gap-1">
          <AlertTriangle className="h-3 w-3" /> OVERDUE
        </Badge>
      );
    }
    switch (p) {
      case "URGENT":
        return <Badge variant="rejected">{p}</Badge>;
      case "HIGH":
        return <Badge variant="pending">{p}</Badge>;
      case "MEDIUM":
        return <Badge variant="sage">{p}</Badge>;
      case "LOW":
        return <Badge variant="neutral">{p}</Badge>;
      default:
        return <Badge variant="outline">{p}</Badge>;
    }
  };

  const getStatusBadge = (s: MaintenanceTaskStatus) => {
    switch (s) {
      case "COMPLETED":
        return <Badge variant="verified">COMPLETED</Badge>;
      case "IN_PROGRESS":
        return <Badge variant="pending">IN PROGRESS</Badge>;
      case "TODO":
        return <Badge variant="sage">TO DO</Badge>;
      case "CANCELLED":
        return <Badge variant="rejected">CANCELLED</Badge>;
      default:
        return <Badge variant="outline">{s}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Filter and Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-4 rounded-xl border border-vana-forest/10 shadow-xs">
        <div className="flex flex-wrap items-center gap-2 flex-1">
          <div className="relative w-full sm:w-64">
            <Search className="h-4 w-4 absolute left-3 top-2.5 text-vana-charcoal/40" />
            <Input
              placeholder="Search tasks..."
              className="pl-9 h-9 text-xs"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-9 px-3 rounded-md border border-vana-charcoal/20 bg-white text-xs text-vana-charcoal"
          >
            <option value="ALL">All Statuses</option>
            <option value="TODO">To Do</option>
            <option value="IN_PROGRESS">In Progress</option>
            <option value="COMPLETED">Completed</option>
            <option value="CANCELLED">Cancelled</option>
          </select>

          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="h-9 px-3 rounded-md border border-vana-charcoal/20 bg-white text-xs text-vana-charcoal"
          >
            <option value="ALL">All Priorities</option>
            <option value="URGENT">Urgent</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>

          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="h-9 px-3 rounded-md border border-vana-charcoal/20 bg-white text-xs text-vana-charcoal"
          >
            <option value="ALL">All Categories</option>
            <option value="IRRIGATION">Irrigation</option>
            <option value="WEEDING">Weeding</option>
            <option value="MULCHING">Mulching</option>
            <option value="FENCING_REPAIR">Fencing Repair</option>
            <option value="REPLANTING_PREP">Replanting Prep</option>
            <option value="PEST_CONTROL">Pest Control</option>
            <option value="SOIL_ENRICHMENT">Soil Enrichment</option>
            <option value="OTHER">Other</option>
          </select>
        </div>

        {canManage && (
          <Button
            size="sm"
            onClick={handleOpenCreateModal}
            className="bg-vana-forest text-white gap-1.5 shrink-0"
          >
            <Plus className="h-4 w-4" /> New Maintenance Task
          </Button>
        )}
      </div>

      {/* Tasks Table / Cards */}
      <Card className="border border-vana-forest/15 bg-white shadow-subtle overflow-hidden">
        <CardContent className="p-0">
          {filteredTasks.length === 0 ? (
            <div className="text-center py-12 px-4 text-vana-charcoal/60 space-y-2">
              <ClipboardList className="h-8 w-8 text-vana-gold/40 mx-auto" />
              <p className="text-sm font-semibold font-manrope text-vana-forest">
                No maintenance tasks match the criteria
              </p>
              <p className="text-xs max-w-sm mx-auto">
                {canManage
                  ? "Schedule follow-up tasks such as irrigation, weeding, or fencing repair to preserve seedling health."
                  : "Assigned tasks will appear here."}
              </p>
              {canManage && (
                <Button
                  size="sm"
                  onClick={handleOpenCreateModal}
                  className="mt-3 bg-vana-forest text-white text-xs"
                >
                  <Plus className="h-3.5 w-3.5 mr-1" /> Create First Task
                </Button>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-vana-forest/5 text-vana-charcoal/80 uppercase text-[10px] font-semibold border-b border-vana-forest/10">
                  <tr>
                    <th className="py-3 px-4">Task</th>
                    <th className="py-3 px-4">Project</th>
                    <th className="py-3 px-4">Category</th>
                    <th className="py-3 px-4">Priority</th>
                    <th className="py-3 px-4">Due Date</th>
                    <th className="py-3 px-4">Assignee</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-vana-forest/10">
                  {filteredTasks.map((task) => {
                    const isOverdue =
                      task.due_date < todayStr &&
                      task.status !== "COMPLETED" &&
                      task.status !== "CANCELLED";
                    const isAssignee = task.assigned_to_id === currentUserId;
                    const canExecute = isAssignee || canManage;

                    return (
                      <tr
                        key={task.id}
                        className={`hover:bg-vana-forest/5 transition-colors ${
                          isOverdue ? "bg-vana-crimson/5" : ""
                        }`}
                      >
                        <td className="py-3 px-4 font-semibold text-vana-charcoal max-w-xs">
                          <div>{task.title}</div>
                          {task.description && (
                            <div className="text-[11px] text-vana-charcoal/60 line-clamp-1 font-normal mt-0.5">
                              {task.description}
                            </div>
                          )}
                        </td>
                        <td className="py-3 px-4 font-medium text-vana-forest">
                          {getProjectName(task.project_id)}
                        </td>
                        <td className="py-3 px-4">
                          <span className="font-medium text-vana-charcoal/80">
                            {task.category.replace(/_/g, " ")}
                          </span>
                        </td>
                        <td className="py-3 px-4">{getPriorityBadge(task.priority, isOverdue)}</td>
                        <td
                          className={`py-3 px-4 whitespace-nowrap font-medium ${
                            isOverdue ? "text-vana-crimson font-bold" : "text-vana-charcoal"
                          }`}
                        >
                          {task.due_date}
                        </td>
                        <td className="py-3 px-4 text-vana-charcoal/80">
                          {getUserName(task.assigned_to_id)}
                        </td>
                        <td className="py-3 px-4">{getStatusBadge(task.status)}</td>
                        <td className="py-3 px-4 text-right space-x-1 whitespace-nowrap">
                          {/* Start task */}
                          {task.status === "TODO" && canExecute && (
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-7 text-xs border-vana-forest/30 text-vana-forest hover:bg-vana-forest/10"
                              onClick={() => onStartTask(task.id)}
                            >
                              <Play className="h-3 w-3 mr-1" /> Start
                            </Button>
                          )}

                          {/* Complete task */}
                          {task.status === "IN_PROGRESS" && canExecute && (
                            <Button
                              size="sm"
                              className="h-7 text-xs bg-emerald-800 text-white hover:bg-emerald-700"
                              onClick={() => handleOpenCompleteModal(task)}
                            >
                              <CheckCircle className="h-3 w-3 mr-1" /> Complete
                            </Button>
                          )}

                          {/* Cancel task */}
                          {(task.status === "TODO" || task.status === "IN_PROGRESS") &&
                            canManage && (
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-7 text-xs text-vana-crimson hover:bg-vana-crimson/10"
                                onClick={() => handleOpenCancelModal(task)}
                              >
                                Cancel
                              </Button>
                            )}

                          {/* Reopen task */}
                          {task.status === "COMPLETED" && canManage && (
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-7 text-xs border-vana-gold/40 text-[#8C6228] hover:bg-vana-gold/10"
                              onClick={() => handleOpenReopenModal(task)}
                            >
                              <RotateCcw className="h-3 w-3 mr-1" /> Reopen
                            </Button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ===================================================================== */}
      {/* Create Task Modal */}
      {/* ===================================================================== */}
      <Dialog open={isCreateModalOpen} onOpenChange={setIsCreateModalOpen}>
        <DialogContent className="max-w-md bg-white p-6 rounded-xl border border-vana-forest/15">
          <form onSubmit={handleSubmitCreate} className="space-y-4">
            <DialogHeader>
              <DialogTitle className="text-lg font-bold font-manrope text-vana-forest">
                Create Maintenance Task
              </DialogTitle>
              <DialogDescription className="text-xs text-vana-charcoal/70">
                Assign post-planting care, irrigation, or boundary maintenance.
              </DialogDescription>
            </DialogHeader>

            {createError && (
              <div className="p-3 bg-vana-crimson/10 text-vana-crimson rounded-lg text-xs flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{createError}</span>
              </div>
            )}

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-vana-charcoal block mb-1">
                  Target Project *
                </label>
                <select
                  value={taskProjectId}
                  onChange={(e) => setTaskProjectId(e.target.value)}
                  className="w-full h-9 px-3 rounded-md border border-vana-charcoal/20 bg-white"
                  required
                >
                  <option value="">Select Project...</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="font-semibold text-vana-charcoal block mb-1">
                  Task Title *
                </label>
                <Input
                  placeholder="e.g. Weed perimeter along seedling bed B"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="h-9 text-xs"
                  required
                />
              </div>

              <div>
                <label className="font-semibold text-vana-charcoal block mb-1">
                  Description
                </label>
                <textarea
                  placeholder="Provide field instructions or required tools..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={2}
                  className="w-full p-2.5 rounded-md border border-vana-charcoal/20 text-xs"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-vana-charcoal block mb-1">
                    Category *
                  </label>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value as MaintenanceTaskCategory)}
                    className="w-full h-9 px-2.5 rounded-md border border-vana-charcoal/20 bg-white"
                  >
                    <option value="IRRIGATION">Irrigation</option>
                    <option value="WEEDING">Weeding</option>
                    <option value="MULCHING">Mulching</option>
                    <option value="FENCING_REPAIR">Fencing Repair</option>
                    <option value="REPLANTING_PREP">Replanting Prep</option>
                    <option value="PEST_CONTROL">Pest Control</option>
                    <option value="SOIL_ENRICHMENT">Soil Enrichment</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>

                <div>
                  <label className="font-semibold text-vana-charcoal block mb-1">
                    Priority *
                  </label>
                  <select
                    value={priority}
                    onChange={(e) => setPriority(e.target.value as MaintenanceTaskPriority)}
                    className="w-full h-9 px-2.5 rounded-md border border-vana-charcoal/20 bg-white"
                  >
                    <option value="LOW">Low</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="HIGH">High</option>
                    <option value="URGENT">Urgent</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-vana-charcoal block mb-1">
                    Due Date *
                  </label>
                  <Input
                    type="date"
                    value={dueDate}
                    onChange={(e) => setDueDate(e.target.value)}
                    className="h-9 text-xs"
                    required
                  />
                </div>

                <div>
                  <label className="font-semibold text-vana-charcoal block mb-1">
                    Assignee
                  </label>
                  <select
                    value={assigneeId}
                    onChange={(e) => setAssigneeId(e.target.value)}
                    className="w-full h-9 px-2.5 rounded-md border border-vana-charcoal/20 bg-white"
                  >
                    <option value="">Unassigned</option>
                    {users.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.full_name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            <DialogFooter className="pt-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setIsCreateModalOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={isSubmittingCreate}
                className="bg-vana-forest text-white"
              >
                {isSubmittingCreate ? "Creating..." : "Create Task"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ===================================================================== */}
      {/* Complete Task Modal */}
      {/* ===================================================================== */}
      <Dialog open={isCompleteModalOpen} onOpenChange={setIsCompleteModalOpen}>
        <DialogContent className="max-w-md bg-white p-6 rounded-xl border border-vana-forest/15">
          <form onSubmit={handleSubmitComplete} className="space-y-4">
            <DialogHeader>
              <DialogTitle className="text-lg font-bold font-manrope text-vana-forest">
                Complete Maintenance Task
              </DialogTitle>
              <DialogDescription className="text-xs text-vana-charcoal/70">
                Record mandatory completion notes for task: "{activeTask?.title}".
              </DialogDescription>
            </DialogHeader>

            {completeError && (
              <div className="p-3 bg-vana-crimson/10 text-vana-crimson rounded-lg text-xs">
                {completeError}
              </div>
            )}

            <div>
              <label className="font-semibold text-vana-charcoal text-xs block mb-1">
                Completion Notes *
              </label>
              <textarea
                value={completionNotes}
                onChange={(e) => setCompletionNotes(e.target.value)}
                rows={3}
                placeholder="Describe completed work, resources utilized, or remaining checks..."
                className="w-full p-2.5 rounded-md border border-vana-charcoal/20 text-xs"
                required
              />
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setIsCompleteModalOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit" size="sm" className="bg-emerald-800 text-white">
                Mark as Completed
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ===================================================================== */}
      {/* Cancel Task Modal */}
      {/* ===================================================================== */}
      <Dialog open={isCancelModalOpen} onOpenChange={setIsCancelModalOpen}>
        <DialogContent className="max-w-md bg-white p-6 rounded-xl border border-vana-crimson/25">
          <form onSubmit={handleSubmitCancel} className="space-y-4">
            <DialogHeader>
              <DialogTitle className="text-lg font-bold font-manrope text-vana-crimson">
                Cancel Task
              </DialogTitle>
              <DialogDescription className="text-xs text-vana-charcoal/70">
                Cancel "{activeTask?.title}" with required justification.
              </DialogDescription>
            </DialogHeader>

            {cancelError && (
              <div className="p-3 bg-vana-crimson/10 text-vana-crimson rounded-lg text-xs">
                {cancelError}
              </div>
            )}

            <div>
              <label className="font-semibold text-vana-charcoal text-xs block mb-1">
                Cancellation Reason *
              </label>
              <textarea
                value={cancellationReason}
                onChange={(e) => setCancellationReason(e.target.value)}
                rows={3}
                placeholder="e.g. Activity cancelled or handled under another contract..."
                className="w-full p-2.5 rounded-md border border-vana-charcoal/20 text-xs"
                required
              />
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setIsCancelModalOpen(false)}
              >
                Back
              </Button>
              <Button type="submit" size="sm" variant="destructive">
                Confirm Cancellation
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ===================================================================== */}
      {/* Reopen Task Modal */}
      {/* ===================================================================== */}
      <Dialog open={isReopenModalOpen} onOpenChange={setIsReopenModalOpen}>
        <DialogContent className="max-w-md bg-white p-6 rounded-xl border border-vana-gold/30">
          <form onSubmit={handleSubmitReopen} className="space-y-4">
            <DialogHeader>
              <DialogTitle className="text-lg font-bold font-manrope text-vana-forest">
                Reopen Maintenance Task
              </DialogTitle>
              <DialogDescription className="text-xs text-vana-charcoal/70">
                Reopening transitions the task back to TODO. Provide audit-logged justification.
              </DialogDescription>
            </DialogHeader>

            {reopenError && (
              <div className="p-3 bg-vana-crimson/10 text-vana-crimson rounded-lg text-xs">
                {reopenError}
              </div>
            )}

            <div>
              <label className="font-semibold text-vana-charcoal text-xs block mb-1">
                Reopening Justification *
              </label>
              <textarea
                value={justification}
                onChange={(e) => setJustification(e.target.value)}
                rows={3}
                placeholder="e.g. Follow-up inspection revealed incomplete weeding in north sector..."
                className="w-full p-2.5 rounded-md border border-vana-charcoal/20 text-xs"
                required
              />
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setIsReopenModalOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit" size="sm" className="bg-vana-gold text-vana-charcoal font-semibold">
                Reopen Task
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};
