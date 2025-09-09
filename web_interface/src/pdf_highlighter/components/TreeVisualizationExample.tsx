// BetterVisExample.tsx
import React, { useEffect, useRef, useState, useContext } from 'react';
import { Network } from 'vis-network/standalone';
import 'vis-network/styles/vis-network.css';
import axiosInstance from '../../axiosSetup';
import { GlobalContext } from '../../GlobalState';

type VisOptions = Record<string, any>;          // quick-and-dirty helper

const TreeVisualizationExample: React.FC<{ highlightId: string }> = ({ highlightId }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [network, setNetwork] = useState<Network | null>(null);

  const globalContext = useContext(GlobalContext);
  if (!globalContext) throw new Error('GlobalContext is undefined');
  const { documentId, updateId } = globalContext;

  /** merge defaults only when the backend didn’t provide them */
  const withZoomDefaults = (opts: VisOptions): VisOptions => {
    const interaction = { ...(opts.interaction ?? {}) };

    if (interaction.navigationButtons === undefined)
      interaction.navigationButtons = true;          // built-in + / – / fit toolbar

    if (interaction.keyboard === undefined)
      interaction.keyboard = true;                    // arrow keys + +/- zoom shortcuts

    if (interaction.zoomSpeed === undefined)
      interaction.zoomSpeed = 0.5;                    // wheel sensitivity

    return { ...opts, interaction };
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        const token   = localStorage.getItem('accessToken');
        const payload = { document_id: documentId, update_id: updateId, id: highlightId };

        const { data } = await axiosInstance.post(
          `${import.meta.env.VITE_BACKEND_URL}/get-nodes-and-edges`,
          payload,
          { headers: { Authorization: `Bearer ${token}` } }
        );

        const { nodes, edges, options } = data;
        const mergedOptions = withZoomDefaults(options ?? {});

        const net = new Network(containerRef.current!, { nodes, edges }, mergedOptions);

        net.once('stabilizationIterationsDone', () => {
          net.setOptions({ physics: false });
          net.fit({ animation: true });
        });

        setNetwork(net);
      } catch (err) {
        console.error('Error fetching graph data:', err);
      }
    };

    fetchData();
    return () => network?.destroy();
  }, [documentId, updateId, highlightId]);

  return (
    <div style={{ width: '100%', height: '600px' }}>
      <div
        ref={containerRef}
        style={{ width: '100%', height: '100%', backgroundColor: '#f8f9fa' }}
      />
    </div>
  );
};

export default TreeVisualizationExample;
