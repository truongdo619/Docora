import React from "react";
import { Droppable, DroppableProps } from "react-beautiful-dnd";

type StrictModeDroppableProps = Omit<DroppableProps, 'children'> & {
  children: DroppableProps['children'];
};

/**
 * Workaround for React 18 / Strict Mode double-invocation issues.
 */
export function StrictModeDroppable({ children, ...droppableProps }: StrictModeDroppableProps) {
  const [enabled, setEnabled] = React.useState(false);

  React.useEffect(() => {
    // Schedule enabling of Droppable on the next animation frame
    const animation = requestAnimationFrame(() => setEnabled(true));
    return () => cancelAnimationFrame(animation);
  }, []);

  if (!enabled) {
    return null; // Defer Droppable until the next frame
  }

  return <Droppable {...droppableProps}>{children}</Droppable>;
}
