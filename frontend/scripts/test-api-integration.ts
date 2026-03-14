/**
 * Frontend API Integration Test Script
 *
 * This script tests the frontend API client against the backend server.
 * Run with: npx tsx scripts/test-api-integration.ts
 *
 * Prerequisites:
 * - Backend server running on http://localhost:8000
 * - Or set API_URL environment variable
 */

import { projectApi, characterApi, chapterApi, sceneApi, worldSettingApi, healthApi } from '../lib/api-client';
import type { ProjectCreate, CharacterCreate, WorldSettingCreate, ChapterCreate, SceneCreate } from '../lib/types';

const API_BASE_URL = process.env.API_URL || 'http://localhost:8000';

// Colors for terminal output
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
};

function log(message: string, color: keyof typeof colors = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function logTest(testName: string) {
  log(`\n▶ ${testName}`, 'cyan');
}

function logSuccess(message: string) {
  log(`  ✓ ${message}`, 'green');
}

function logError(message: string) {
  log(`  ✗ ${message}`, 'red');
}

function logInfo(message: string) {
  log(`  ℹ ${message}`, 'blue');
}

// Test results tracker
interface TestResult {
  name: string;
  passed: boolean;
  error?: string;
}

const results: TestResult[] = [];

async function runTest(name: string, testFn: () => Promise<void>) {
  logTest(name);
  try {
    await testFn();
    results.push({ name, passed: true });
    logSuccess('PASSED');
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    results.push({ name, passed: false, error: errorMsg });
    logError(`FAILED: ${errorMsg}`);
  }
}

// ============================================================================
// Integration Tests
// ============================================================================

async function runAllTests() {
  log('\n🚀 AI Novel Agent - Frontend API Integration Tests', 'yellow');
  log(`Backend URL: ${API_BASE_URL}`, 'blue');

  // Test IDs for cleanup
  let testProjectId: string | null = null;
  let testCharacterId: string | null = null;
  let testWorldSettingId: string | null = null;
  let testChapterId: string | null = null;
  let testSceneId: string | null = null;

  // ------------------------------------------------------------------------
  // Health Check
  // ------------------------------------------------------------------------
  await runTest('Health Check', async () => {
    const health = await healthApi.check();
    if (health.status !== 'healthy') {
      throw new Error(`Expected status 'healthy', got '${health.status}'`);
    }
    logInfo(`Version: ${health.version}`);
  });

  // ------------------------------------------------------------------------
  // Projects API
  // ------------------------------------------------------------------------
  await runTest('Projects: List (empty)', async () => {
    const response = await projectApi.list({ skip: 0, limit: 10 }) as unknown[];
    logInfo(`Found ${response.length} projects`);
  });

  await runTest('Projects: Create', async () => {
    const data: ProjectCreate = {
      name: 'Test Project',
      genre: 'Fantasy',
      target_audience: 'Young Adult',
      summary: 'A test novel project',
    };
    const project = await projectApi.create(data) as { id: string; name: string };
    testProjectId = project.id;
    logInfo(`Created project with ID: ${project.id}`);
  });

  await runTest('Projects: Get by ID', async () => {
    if (!testProjectId) throw new Error('No project ID available');
    const project = await projectApi.getById(testProjectId) as { id: string; name: string };
    if (project.name !== 'Test Project') {
      throw new Error(`Expected name 'Test Project', got '${project.name}'`);
    }
  });

  await runTest('Projects: Update', async () => {
    if (!testProjectId) throw new Error('No project ID available');
    const updated = await projectApi.update(testProjectId, {
      genre: 'Science Fiction',
    }) as { genre: string };
    if (updated.genre !== 'Science Fiction') {
      throw new Error(`Expected genre 'Science Fiction', got '${updated.genre}'`);
    }
  });

  // ------------------------------------------------------------------------
  // Characters API
  // ------------------------------------------------------------------------
  await runTest('Characters: Create', async () => {
    if (!testProjectId) throw new Error('No project ID available');
    const data: CharacterCreate = {
      project_id: testProjectId,
      name: 'Test Hero',
      role: 'protagonist',
      profile: { age: 25, background: 'A brave hero' },
    };
    const character = await characterApi.create(data) as { id: string; name: string };
    testCharacterId = character.id;
    logInfo(`Created character with ID: ${character.id}`);
  });

  await runTest('Characters: List', async () => {
    if (!testProjectId) throw new Error('No project ID available');
    const characters = await characterApi.list(testProjectId) as { id: string; name: string }[];
    if (characters.length === 0) {
      throw new Error('Expected at least one character');
    }
    logInfo(`Found ${characters.length} character(s)`);
  });

  await runTest('Characters: Get', async () => {
    if (!testCharacterId) throw new Error('No character ID available');
    const character = await characterApi.get(testCharacterId) as { name: string };
    if (character.name !== 'Test Hero') {
      throw new Error(`Expected name 'Test Hero', got '${character.name}'`);
    }
  });

  // ------------------------------------------------------------------------
  // WorldSettings API
  // ------------------------------------------------------------------------
  await runTest('WorldSettings: Create', async () => {
    if (!testProjectId) throw new Error('No project ID available');
    const data: WorldSettingCreate = {
      project_id: testProjectId,
      category: 'geography',
      name: 'Test Castle',
      content: 'A magnificent castle on a hill',
    };
    const setting = await worldSettingApi.create(data) as { id: string; name: string };
    testWorldSettingId = setting.id;
    logInfo(`Created world setting with ID: ${setting.id}`);
  });

  await runTest('WorldSettings: List', async () => {
    if (!testProjectId) throw new Error('No project ID available');
    const settings = await worldSettingApi.list(testProjectId) as { id: string; name: string }[];
    if (settings.length === 0) {
      throw new Error('Expected at least one world setting');
    }
    logInfo(`Found ${settings.length} setting(s)`);
  });

  await runTest('WorldSettings: Filter by category', async () => {
    if (!testProjectId) throw new Error('No project ID available');
    const settings = await worldSettingApi.getByCategory(testProjectId, 'geography') as {
      category: string;
    }[];
    if (settings.length === 0) {
      throw new Error('Expected at least one geography setting');
    }
    if (settings[0].category !== 'geography') {
      throw new Error(`Expected category 'geography', got '${settings[0].category}'`);
    }
  });

  // ------------------------------------------------------------------------
  // Chapters API
  // ------------------------------------------------------------------------
  await runTest('Chapters: Create', async () => {
    if (!testProjectId) throw new Error('No project ID available');
    const data: ChapterCreate = {
      project_id: testProjectId,
      chapter_number: 1,
      title: 'The Beginning',
      outline: 'Our hero starts their journey',
    };
    const chapter = await chapterApi.create(data) as { id: string; chapter_number: number };
    testChapterId = chapter.id;
    logInfo(`Created chapter with ID: ${chapter.id}`);
  });

  await runTest('Chapters: List', async () => {
    if (!testProjectId) throw new Error('No project ID available');
    const chapters = await chapterApi.list(testProjectId) as { id: string; chapter_number: number }[];
    if (chapters.length === 0) {
      throw new Error('Expected at least one chapter');
    }
    logInfo(`Found ${chapters.length} chapter(s)`);
  });

  // ------------------------------------------------------------------------
  // Scenes API
  // ------------------------------------------------------------------------
  await runTest('Scenes: Create', async () => {
    if (!testChapterId) throw new Error('No chapter ID available');
    const data: SceneCreate = {
      chapter_id: testChapterId,
      scene_order: 1,
      location: 'Test Castle',
      content: 'The hero arrives at the castle gates',
    };
    const scene = await sceneApi.create(data) as { id: string; scene_order: number };
    testSceneId = scene.id;
    logInfo(`Created scene with ID: ${scene.id}`);
  });

  await runTest('Scenes: List', async () => {
    if (!testChapterId) throw new Error('No chapter ID available');
    const scenes = await sceneApi.list(testChapterId) as { id: string; scene_order: number }[];
    if (scenes.length === 0) {
      throw new Error('Expected at least one scene');
    }
    logInfo(`Found ${scenes.length} scene(s)`);
  });

  // ------------------------------------------------------------------------
  // Cleanup
  // ------------------------------------------------------------------------
  await runTest('Cleanup: Delete Scene', async () => {
    if (!testSceneId) throw new Error('No scene ID available');
    await sceneApi.delete(testSceneId);
    logInfo('Deleted test scene');
  });

  await runTest('Cleanup: Delete Chapter', async () => {
    if (!testChapterId) throw new Error('No chapter ID available');
    await chapterApi.delete(testChapterId);
    logInfo('Deleted test chapter');
  });

  await runTest('Cleanup: Delete Character', async () => {
    if (!testCharacterId) throw new Error('No character ID available');
    await characterApi.delete(testCharacterId);
    logInfo('Deleted test character');
  });

  await runTest('Cleanup: Delete WorldSetting', async () => {
    if (!testWorldSettingId) throw new Error('No world setting ID available');
    await worldSettingApi.delete(testWorldSettingId);
    logInfo('Deleted test world setting');
  });

  await runTest('Cleanup: Delete Project', async () => {
    if (!testProjectId) throw new Error('No project ID available');
    await projectApi.delete(testProjectId);
    logInfo('Deleted test project');
  });

  // ------------------------------------------------------------------------
  // Summary
  // ------------------------------------------------------------------------
  log('\n' + '='.repeat(50), 'yellow');
  log('TEST SUMMARY', 'yellow');
  log('='.repeat(50), 'yellow');

  const passed = results.filter(r => r.passed).length;
  const failed = results.filter(r => !r.passed).length;

  results.forEach(result => {
    const status = result.passed ? '✓' : '✗';
    const color = result.passed ? 'green' : 'red';
    log(`${status} ${result.name}`, color);
    if (!result.passed && result.error) {
      log(`    Error: ${result.error}`, 'red');
    }
  });

  log('\n' + '-'.repeat(50), 'yellow');
  log(`Total: ${results.length} | Passed: ${passed} | Failed: ${failed}`, 'yellow');

  if (failed > 0) {
    process.exit(1);
  } else {
    log('\n✨ All tests passed!', 'green');
    process.exit(0);
  }
}

// Run tests
runAllTests().catch(error => {
  logError(`Unhandled error: ${error}`);
  process.exit(1);
});
