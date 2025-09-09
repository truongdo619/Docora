import React, { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

/**
 * MyCustomNode:
 * A node with four source handles and four target handles,
 * each handle assigned a unique ID so edges can specifically connect.
 */
function MyCustomNode({ data }: NodeProps) {
  return (
    <div
      style={{
        padding: 10,
        border: '1px solid #555',
        borderRadius: 5,
        minWidth: 150,
        maxWidth: 200,
        textAlign: 'center',
      }}
    >
      {/* Node label */}
      <div>{data.label}</div>

      {/* SOURCE handles (unique IDs for each side) */}
      <Handle
        type="source"
        position={Position.Left}
        id="source-left"
        style={{ background: '#555' }}
      />
      <Handle
        type="source"
        position={Position.Right}
        id="source-right"
        style={{ background: '#555' }}
      />
      <Handle
        type="source"
        position={Position.Top}
        id="source-top"
        style={{ background: '#555' }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="source-bottom"
        style={{ background: '#555' }}
      />

      {/* TARGET handles (unique IDs for each side) */}
      <Handle
        type="target"
        position={Position.Left}
        id="target-left"
        style={{ background: '#555' }}
      />
      <Handle
        type="target"
        position={Position.Right}
        id="target-right"
        style={{ background: '#555' }}
      />
      <Handle
        type="target"
        position={Position.Top}
        id="target-top"
        style={{ background: '#555' }}
      />
      <Handle
        type="target"
        position={Position.Bottom}
        id="target-bottom"
        style={{ background: '#555' }}
      />
    </div>
  );
}

export default memo(MyCustomNode);
