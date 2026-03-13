/**
 * Project Store - Zustand state management for projects
 *
 * Handles project list, single project detail, and CRUD operations.
 */

import { create } from 'zustand';
import { projectApi } from '@/lib/api-client';
import type { Project, ProjectCreate, ProjectUpdate } from '@/lib/types';
import { ApiError } from '@/lib/api-client';

interface ProjectState {
  // Project list state
  projects: Project[];
  projectsTotal: number;
  projectsLoading: boolean;
  projectsError: string | null;
  // Aliases for convenience
  loading: boolean;
  error: string | null;

  // Single project state
  currentProject: Project | null;
  currentProjectLoading: boolean;
  currentProjectError: string | null;

  // Actions
  fetchProjects: (params?: { skip?: number; limit?: number }) => Promise<void>;
  fetchProject: (id: string) => Promise<void>;
  createProject: (data: ProjectCreate) => Promise<Project>;
  updateProject: (id: string, data: ProjectUpdate) => Promise<void>;
  deleteProject: (id: string) => Promise<void>;
  clearCurrentProject: () => void;
  clearErrors: () => void;
}

export const useProjectStore = create<ProjectState>((set) => ({
  // Initial state
  projects: [],
  projectsTotal: 0,
  projectsLoading: false,
  projectsError: null,
  // Aliases for convenience
  loading: false,
  error: null,
  currentProject: null,
  currentProjectLoading: false,
  currentProjectError: null,

  // Fetch project list
  fetchProjects: async (params = { skip: 0, limit: 100 }) => {
    set({ projectsLoading: true, projectsError: null, loading: true, error: null });
    try {
      const response = await projectApi.list(params) as {
        items: Project[];
        total: number;
        skip: number;
        limit: number;
      };
      set({
        projects: response.items || [],
        projectsTotal: response.total,
        projectsLoading: false,
        loading: false,
      });
    } catch (err) {
      const message = err instanceof ApiError ? err.detail : 'Failed to load projects';
      set({ projectsError: message, projectsLoading: false, error: message, loading: false });
    }
  },

  // Fetch single project
  fetchProject: async (id: string) => {
    set({ currentProjectLoading: true, currentProjectError: null });
    try {
      const project = await projectApi.getById(id) as Project;
      set({
        currentProject: project,
        currentProjectLoading: false,
      });
    } catch (err) {
      const message = err instanceof ApiError ? err.detail : 'Failed to load project';
      set({ currentProjectError: message, currentProjectLoading: false });
      throw err;
    }
  },

  // Create new project
  createProject: async (data: ProjectCreate) => {
    set({ projectsError: null });
    try {
      const newProject = await projectApi.create(data) as Project;
      // Add to list
      set((state) => ({
        projects: [newProject, ...state.projects],
        projectsTotal: state.projectsTotal + 1,
      }));
      return newProject;
    } catch (err) {
      const message = err instanceof ApiError ? err.detail : 'Failed to create project';
      set({ projectsError: message });
      throw err;
    }
  },

  // Update project
  updateProject: async (id: string, data: ProjectUpdate) => {
    set({ projectsError: null });
    try {
      const updatedProject = await projectApi.update(id, data) as Project;
      // Update in list
      set((state) => ({
        projects: state.projects.map((p) =>
          p.id === id ? updatedProject : p
        ),
        // Also update currentProject if it's the same one
        currentProject:
          state.currentProject?.id === id
            ? updatedProject
            : state.currentProject,
      }));
    } catch (err) {
      const message = err instanceof ApiError ? err.detail : 'Failed to update project';
      set({ projectsError: message });
      throw err;
    }
  },

  // Delete project
  deleteProject: async (id: string) => {
    set({ projectsError: null });
    try {
      await projectApi.delete(id);
      // Remove from list
      set((state) => ({
        projects: state.projects.filter((p) => p.id !== id),
        projectsTotal: state.projectsTotal - 1,
        currentProject:
          state.currentProject?.id === id ? null : state.currentProject,
      }));
    } catch (err) {
      const message = err instanceof ApiError ? err.detail : 'Failed to delete project';
      set({ projectsError: message });
      throw err;
    }
  },

  // Clear current project
  clearCurrentProject: () => {
    set({ currentProject: null, currentProjectError: null });
  },

  // Clear all errors
  clearErrors: () => {
    set({ projectsError: null, currentProjectError: null });
  },
}));
