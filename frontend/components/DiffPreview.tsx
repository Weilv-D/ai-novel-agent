"use client";

interface DiffPreviewProps {
  before: string;
  after: string;
  title?: string;
}

export function DiffPreview({ before, after, title }: DiffPreviewProps) {
  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      {title && (
        <div className="bg-gray-50 px-4 py-2 border-b border-gray-200 text-sm font-medium text-gray-700">
          {title}
        </div>
      )}
      <div className="grid grid-cols-2 divide-x divide-gray-200">
        <div className="p-4">
          <div className="text-xs font-medium text-red-600 mb-2">修改前</div>
          <div className="text-sm text-gray-700 whitespace-pre-wrap bg-red-50 p-3 rounded">
            {before || "（空）"}
          </div>
        </div>
        <div className="p-4">
          <div className="text-xs font-medium text-green-600 mb-2">修改后</div>
          <div className="text-sm text-gray-700 whitespace-pre-wrap bg-green-50 p-3 rounded">
            {after || "（空）"}
          </div>
        </div>
      </div>
    </div>
  );
}
