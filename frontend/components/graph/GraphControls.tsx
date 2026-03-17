"use client";

import { Panel, useReactFlow } from "@xyflow/react";

interface LayoutOption {
  value: string;
  label: string;
}

interface GraphControlsProps {
  layout: string;
  layoutOptions: LayoutOption[];
  onLayoutChange: (layout: string) => void;
}

export function GraphControls({ layout, layoutOptions, onLayoutChange }: GraphControlsProps) {
  const { fitView, zoomIn, zoomOut } = useReactFlow();

  return (
    <Panel position="top-right">
      <div className="ink-graph__panel">
        <div className="flex items-center gap-2">
          <button type="button" className="ink-graph__button" onClick={() => zoomIn({ duration: 180 })}>
            放大
          </button>
          <button type="button" className="ink-graph__button" onClick={() => zoomOut({ duration: 180 })}>
            缩小
          </button>
          <button
            type="button"
            className="ink-graph__button"
            onClick={() => fitView({ duration: 220, padding: 0.18 })}
          >
            居中
          </button>
        </div>
        <div className="flex flex-wrap gap-2">
          {layoutOptions.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => onLayoutChange(option.value)}
              className={`ink-graph__button ${layout === option.value ? "ink-graph__button--active" : ""}`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>
    </Panel>
  );
}
