import * as vscode from 'vscode';
import * as path from 'path';
import { ReferenceEvolution, EvolutionEntry } from '../types/living-document.types';

/**
 * Tracks how references evolve over time in Living Documents
 * This is critical for maintaining document relevance as codebases change
 */
export class ReferenceEvolutionTracker {
    private evolutionMap: Map<string, ReferenceEvolution> = new Map();
    private persistencePath: string;
    private saveDebouncer: NodeJS.Timeout | null = null;

    constructor(private context: vscode.ExtensionContext) {
        this.persistencePath = path.join(context.globalStorageUri.fsPath, 'evolution-history.json');
        this.loadEvolutionHistory();
    }

    /**
     * Track a reference evolution event
     */
    async trackEvolution(
        documentPath: string,
        oldRef: string,
        newRef: string,
        abstractedRef: string,
        changeType: 'rename' | 'move' | 'refactor' | 'update' = 'update'
    ): Promise<void> {
        // Find existing evolution or create new one
        const evolution = this.findEvolutionChain(oldRef) || {
            originalReference: oldRef,
            currentReference: newRef,
            abstractedForm: abstractedRef,
            firstSeen: new Date(),
            lastUpdated: new Date(),
            documentPaths: new Set<string>([documentPath]),
            evolutionChain: []
        };

        // Add new evolution entry
        const entry: EvolutionEntry = {
            timestamp: new Date(),
            fromReference: oldRef,
            toReference: newRef,
            abstractedForm: abstractedRef,
            changeType,
            documentPath,
            confidence: this.calculateConfidence(oldRef, newRef)
        };

        evolution.evolutionChain.push(entry);
        evolution.currentReference = newRef;
        evolution.abstractedForm = abstractedRef;
        evolution.lastUpdated = new Date();
        evolution.documentPaths.add(documentPath);

        // Update the map with new reference as key
        this.evolutionMap.set(newRef, evolution);
        
        // Also keep old reference pointing to same evolution for lookup
        this.evolutionMap.set(oldRef, evolution);

        // Persist changes (debounced)
        this.schedulePersistence();

        // Emit event for other components
        this.emitEvolutionEvent(evolution, entry);
    }

    /**
     * Get evolution history for a reference
     */
    async getEvolutionHistory(reference: string): Promise<ReferenceEvolution | null> {
        return this.evolutionMap.get(reference) || null;
    }

    /**
     * Find all documents affected by a reference change
     */
    async findAffectedDocuments(reference: string): Promise<string[]> {
        const evolution = await this.getEvolutionHistory(reference);
        if (!evolution) return [];

        return Array.from(evolution.documentPaths);
    }

    /**
     * Get all references that evolved from an original reference
     */
    async getEvolutionDescendants(originalRef: string): Promise<string[]> {
        const evolution = await this.getEvolutionHistory(originalRef);
        if (!evolution) return [];

        const descendants = new Set<string>();
        evolution.evolutionChain.forEach(entry => {
            descendants.add(entry.toReference);
        });

        return Array.from(descendants);
    }

    /**
     * Analyze evolution patterns for insights
     */
    async analyzeEvolutionPatterns(): Promise<{
        mostEvolved: Array<{ reference: string; changes: number }>;
        recentChanges: EvolutionEntry[];
        affectedDocuments: number;
    }> {
        const evolutions = Array.from(new Set(this.evolutionMap.values()));
        
        // Find most frequently evolved references
        const mostEvolved = evolutions
            .map(e => ({
                reference: e.currentReference,
                changes: e.evolutionChain.length
            }))
            .sort((a, b) => b.changes - a.changes)
            .slice(0, 10);

        // Get recent changes across all evolutions
        const recentChanges = evolutions
            .flatMap(e => e.evolutionChain)
            .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
            .slice(0, 20);

        // Count total affected documents
        const affectedDocuments = new Set(
            evolutions.flatMap(e => Array.from(e.documentPaths))
        ).size;

        return { mostEvolved, recentChanges, affectedDocuments };
    }

    /**
     * Merge evolution histories when references converge
     */
    async mergeEvolutions(ref1: string, ref2: string): Promise<ReferenceEvolution | null> {
        const evolution1 = await this.getEvolutionHistory(ref1);
        const evolution2 = await this.getEvolutionHistory(ref2);

        if (!evolution1 || !evolution2) return null;

        // Merge the evolution chains chronologically
        const mergedChain = [...evolution1.evolutionChain, ...evolution2.evolutionChain]
            .sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());

        // Create merged evolution
        const merged: ReferenceEvolution = {
            originalReference: evolution1.firstSeen < evolution2.firstSeen 
                ? evolution1.originalReference 
                : evolution2.originalReference,
            currentReference: ref2, // Use the target reference
            abstractedForm: evolution2.abstractedForm,
            firstSeen: new Date(Math.min(
                evolution1.firstSeen.getTime(),
                evolution2.firstSeen.getTime()
            )),
            lastUpdated: new Date(),
            documentPaths: new Set([
                ...evolution1.documentPaths,
                ...evolution2.documentPaths
            ]),
            evolutionChain: mergedChain
        };

        // Update all references to point to merged evolution
        [ref1, ref2, ...this.getAllReferencesInChain(merged)].forEach(ref => {
            this.evolutionMap.set(ref, merged);
        });

        this.schedulePersistence();
        return merged;
    }

    /**
     * Clean up stale evolutions
     */
    async cleanupStaleEvolutions(daysOld: number = 90): Promise<number> {
        const cutoffDate = new Date();
        cutoffDate.setDate(cutoffDate.getDate() - daysOld);

        const staleEvolutions: string[] = [];

        this.evolutionMap.forEach((evolution, key) => {
            if (evolution.lastUpdated < cutoffDate && 
                evolution.evolutionChain.length === 0) {
                staleEvolutions.push(key);
            }
        });

        staleEvolutions.forEach(key => this.evolutionMap.delete(key));
        
        if (staleEvolutions.length > 0) {
            this.schedulePersistence();
        }

        return staleEvolutions.length;
    }

    // Private methods

    private findEvolutionChain(reference: string): ReferenceEvolution | null {
        // Direct lookup first
        const direct = this.evolutionMap.get(reference);
        if (direct) return direct;

        // Search through all evolutions for this reference
        for (const evolution of this.evolutionMap.values()) {
            const inChain = evolution.evolutionChain.some(
                entry => entry.fromReference === reference || 
                         entry.toReference === reference
            );
            if (inChain) return evolution;
        }

        return null;
    }

    private calculateConfidence(oldRef: string, newRef: string): number {
        // Simple similarity calculation
        const similarity = this.stringSimilarity(oldRef, newRef);
        
        // Boost confidence if paths share common segments
        const oldParts = oldRef.split(/[\/\\]/);
        const newParts = newRef.split(/[\/\\]/);
        const commonParts = oldParts.filter(part => newParts.includes(part)).length;
        const pathSimilarity = commonParts / Math.max(oldParts.length, newParts.length);

        return (similarity + pathSimilarity) / 2;
    }

    private stringSimilarity(str1: string, str2: string): number {
        const longer = str1.length > str2.length ? str1 : str2;
        const shorter = str1.length > str2.length ? str2 : str1;
        
        if (longer.length === 0) return 1.0;
        
        const editDistance = this.levenshteinDistance(longer, shorter);
        return (longer.length - editDistance) / longer.length;
    }

    private levenshteinDistance(str1: string, str2: string): number {
        const matrix: number[][] = [];

        for (let i = 0; i <= str2.length; i++) {
            matrix[i] = [i];
        }

        for (let j = 0; j <= str1.length; j++) {
            matrix[0][j] = j;
        }

        for (let i = 1; i <= str2.length; i++) {
            for (let j = 1; j <= str1.length; j++) {
                if (str2.charAt(i - 1) === str1.charAt(j - 1)) {
                    matrix[i][j] = matrix[i - 1][j - 1];
                } else {
                    matrix[i][j] = Math.min(
                        matrix[i - 1][j - 1] + 1,
                        matrix[i][j - 1] + 1,
                        matrix[i - 1][j] + 1
                    );
                }
            }
        }

        return matrix[str2.length][str1.length];
    }

    private getAllReferencesInChain(evolution: ReferenceEvolution): string[] {
        const refs = new Set<string>();
        evolution.evolutionChain.forEach(entry => {
            refs.add(entry.fromReference);
            refs.add(entry.toReference);
        });
        return Array.from(refs);
    }

    private emitEvolutionEvent(evolution: ReferenceEvolution, entry: EvolutionEntry): void {
        // Emit event for other components to react to evolution
        vscode.commands.executeCommand('coachntt.internal.evolutionTracked', {
            evolution,
            entry
        });
    }

    private schedulePersistence(): void {
        if (this.saveDebouncer) {
            clearTimeout(this.saveDebouncer);
        }

        this.saveDebouncer = setTimeout(() => {
            this.persistEvolutionHistory();
        }, 1000); // Save after 1 second of inactivity
    }

    private async persistEvolutionHistory(): Promise<void> {
        try {
            // Convert Map to serializable format
            const data = {
                version: '1.0',
                timestamp: new Date().toISOString(),
                evolutions: Array.from(this.evolutionMap.entries()).map(([key, value]) => ({
                    key,
                    value: {
                        ...value,
                        documentPaths: Array.from(value.documentPaths),
                        firstSeen: value.firstSeen.toISOString(),
                        lastUpdated: value.lastUpdated.toISOString(),
                        evolutionChain: value.evolutionChain.map(entry => ({
                            ...entry,
                            timestamp: entry.timestamp.toISOString()
                        }))
                    }
                }))
            };

            await vscode.workspace.fs.writeFile(
                vscode.Uri.file(this.persistencePath),
                Buffer.from(JSON.stringify(data, null, 2))
            );
        } catch (error) {
            console.error('Failed to persist evolution history:', error);
        }
    }

    private async loadEvolutionHistory(): Promise<void> {
        try {
            const data = await vscode.workspace.fs.readFile(
                vscode.Uri.file(this.persistencePath)
            );
            const parsed = JSON.parse(data.toString());

            // Reconstruct the Map from saved data
            parsed.evolutions.forEach((item: any) => {
                const evolution: ReferenceEvolution = {
                    ...item.value,
                    documentPaths: new Set(item.value.documentPaths),
                    firstSeen: new Date(item.value.firstSeen),
                    lastUpdated: new Date(item.value.lastUpdated),
                    evolutionChain: item.value.evolutionChain.map((entry: any) => ({
                        ...entry,
                        timestamp: new Date(entry.timestamp)
                    }))
                };
                this.evolutionMap.set(item.key, evolution);
            });
        } catch (error) {
            // File doesn't exist yet or is corrupted - start fresh
            console.log('No evolution history found, starting fresh');
        }
    }
}