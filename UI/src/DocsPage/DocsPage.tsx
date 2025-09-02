// DocsPage.tsx
import React from "react";
import { MuiMarkdown, defaultOverrides } from "mui-markdown";
import {
  Box,
  CssBaseline,
  Drawer,
  Toolbar,
  List,
  ListItemButton,
  ListItemText,
  ListItemIcon,
  Divider,
  Hidden,
  Collapse,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from "@mui/material";
import { ExpandLess, ExpandMore } from "@mui/icons-material";
import { SelectChangeEvent } from "@mui/material/Select";
import { useParams, useNavigate, Link as RouterLink } from "react-router-dom";
import LogoImg from "../assets/images/logo.png";
import Footer from "../HomePage/components/Footer";

/* -------------------------------------------------------------------------- */
/*                               Version assets                               */
/* -------------------------------------------------------------------------- */

// v3.1 markdown
import md31Overview from "./markdown/v1.0/overview.md?raw";
import md31Installation from "./markdown/v1.0/installation.md?raw";
import md31Usage from "./markdown/v1.0/quickstart.md?raw";
import md31Login from "./markdown/v1.0/login-signup.md?raw";
import md31DocManagement from "./markdown/v1.0/document-management.md?raw";
import md31FilteringFunc from "./markdown/v1.0/filtering-function.md?raw";
import md31EditingFunc from "./markdown/v1.0/editing-function.md?raw";
import md31DownloadFunc from "./markdown/v1.0/download-function.md?raw";
import md31ResultVisualization from "./markdown/v1.0/result-visualization.md?raw";
import md31SaveCheckpoint from "./markdown/v1.0/save‑checkpoint.md?raw";
import md31ConfirmAnnotations from "./markdown/v1.0/confirm‑annotation.md?raw";
import md31ParagraphSelection from "./markdown/v1.0/paragraph‑selection.md?raw";
import md31Personalization from "./markdown/v1.0/personal-information-update.md?raw";
import md31faq from "./markdown/v1.0/faq.md?raw";
import md31support from "./markdown/v1.0/contact-support.md?raw";

/* -------------------------------------------------------------------------- */
/*                                   Config                                   */
/* -------------------------------------------------------------------------- */

const drawerWidth = 260;
const versions = ["v1.0"] as const;

type DocsTree = {
  [section: string]: {
    title: string;
    pages: {
      [page: string]: { title: string; md?: string };
    };
  };
};

/** Docs tree per‑version */
const docsByVersion: Record<(typeof versions)[number], DocsTree> = {
  "v1.0": {
    "getting-started": {
      title: "Getting started",
      pages: {
        overview: { title: "Overview", md: md31Overview },
        installation: { title: "Installation", md: md31Installation },
        quickstart: { title: "Quickstart", md: md31Usage },
        faq: { title: "Frequently Asked Questions", md: md31faq },
        support: { title: "Contact Support", md: md31support },
      },
    },
    features: {
      title: "Detailed instructions",
      pages: {
        login: { title: "Login & Signup", md: md31Login },
        dashboard: { title: "Document Management", md: md31DocManagement },
        // working_modes: { title: "Working Modes", md: md31WorkingModes },
        result_visualization: { title: "Result Visualization", md: md31ResultVisualization },
        filtering: { title: "Filtering Results", md: md31FilteringFunc },
        editing: { title: "Editing Annotations", md: md31EditingFunc },
        save_checkpoints: { title: "Save Checkpoints", md: md31SaveCheckpoint },
        confirm_annotations: { title: "Confirm Annotations", md: md31ConfirmAnnotations },
        paragraph_selection: { title: "Paragraph Selection", md: md31ParagraphSelection },
        download: { title: "Export Results", md: md31DownloadFunc },
        personalization: { title: "Personal Information Update", md: md31Personalization },
      },
    },
  }
};

/* -------------------------------------------------------------------------- */
/*                                Docs page UI                                */
/* -------------------------------------------------------------------------- */

export default function DocsPage() {
  const { version: rv, section: rs, page: rp } = useParams<{
    version: string;
    section: string;
    page: string;
  }>();
  const navigate = useNavigate();

  /* -------- Resolve version / section / page -------- */
  const version = versions.includes(rv as any) ? (rv as (typeof versions)[number]) : versions[0];
  const docsStructure = docsByVersion[version];

  const sectionKeys = React.useMemo(() => Object.keys(docsStructure), [docsStructure]);
  const section = sectionKeys.includes(rs || "") ? (rs as string) : sectionKeys[0];
  const pageKeys = Object.keys(docsStructure[section].pages);
  const page = pageKeys.includes(rp || "") ? (rp as string) : pageKeys[0];

  /* -------- Sync URL if something was invalid -------- */
  React.useEffect(() => {
    if (rv !== version || rs !== section || rp !== page) {
      navigate(`/docs/${version}/${section}/${page}`, { replace: true });
    }
  }, [rv, rs, rp, version, section, page, navigate]);

  /* -------- Collapse state -------- */
  const [openMap, setOpenMap] = React.useState<Record<string, boolean>>(() => {
    const m: Record<string, boolean> = {};
    sectionKeys.forEach((s) => (m[s] = s === section));
    return m;
  });
  React.useEffect(() => {
    // Reset open map when version changes
    setOpenMap((m) => {
      const n: Record<string, boolean> = {};
      sectionKeys.forEach((s) => (n[s] = s === section));
      return n;
    });
  }, [sectionKeys, section]);

  const toggleSection = (s: string) => () => setOpenMap((m) => ({ ...m, [s]: !m[s] }));

  /* -------- Version change -------- */
  const handleVersion = (e: SelectChangeEvent<string>) => navigate(`/docs/${e.target.value}/${section}/${page}`);

  /* -------- Markdown source -------- */
  const mdSource = React.useMemo(() => {
    const node = docsStructure[section].pages[page];
    const fallback = `# ${node.title}\n\n_Content coming soon._`;
    return (node.md || fallback).replace(/{{version}}/g, version);
  }, [docsStructure, section, page, version]);

  /* -------- Markdown overrides -------- */
  const overrides = {
    ...defaultOverrides,
    // img: {
    //   component: (props: any) => (
    //     <Box
    //       component="img"
    //       {...props}
    //       sx={{ width: "100%", my: 2, border: 1, borderColor: "divider", borderRadius: 1 }}
    //     />
    //   ),
    // },
    h1: { component: "h1", props: { style: { margin: "10px 0", fontSize: "2.25rem", fontWeight: 600 } } },
    h2: { component: "h2", props: { style: { margin: "40px 0 4px", fontSize: "1.625rem", fontWeight: 600 } } },
    h3: { component: "h3", props: { style: { margin: "24px 0 4px", fontSize: "1.25rem", fontWeight: 600 } } },
    pre: {
      props: {
        style: {
          whiteSpace: "pre",
          overflowX: "auto",
          backgroundColor: "#f5f5f5",
          padding: "12px 16px",
          borderRadius: "8px",
          fontSize: "0.875rem",
        },
      },
    },
    code: {
      props: {
        style: {
          fontFamily: "Source Code Pro, monospace",
          fontSize: "0.875rem",
          backgroundColor: "#f5f5f5",
          padding: "2px 6px",
          borderRadius: "4px",
        },
      },
    },
  };

  /* ---------------------------------------------------------------------- */
  /*                                  Render                                 */
  /* ---------------------------------------------------------------------- */
  return (
    <Box sx={{ display: "flex" }}>
      <CssBaseline />

      {/* ---------------- Sidebar ---------------- */}
      <Hidden mdDown>
        <Drawer
          variant="permanent"
          sx={{
            width: drawerWidth,
            flexShrink: 0,
            "& .MuiDrawer-paper": { width: drawerWidth, boxSizing: "border-box" },
          }}
        >
          {/* Logo */}
          <Box component={RouterLink} to="/home" sx={{ display: "flex", justifyContent: "center", py: 3, mb: 2 }}>
            <Box component="img" src={LogoImg} alt="Docora" sx={{ height: 70 }} />
          </Box>

          {/* Version selector */}
          <Box sx={{ px: 2, py: 2 }}>
            <FormControl fullWidth size="small">
              <InputLabel id="ver-label">Version</InputLabel>
              <Select labelId="ver-label" value={version} label="Version" onChange={handleVersion}>
                {versions.map((v) => (
                  <MenuItem key={v} value={v}>
                    {v}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>

          {/* Nav list */}
          <List
            component="nav"
            dense
            disablePadding
            sx={{
              px: 1,
              borderLeft: 1,
              borderColor: "divider",
              "& .MuiListItemButton-root": {
                py: 0.6,
                pl: 3.5,
                pr: 1,
                borderRadius: 1,
                "&.Mui-selected": {
                  bgcolor: "primary.50",
                  color: "primary.main",
                  "&:hover": { bgcolor: "primary.50" },
                },
                "&:hover": { bgcolor: "action.hover" },
              },
            }}
          >
            {sectionKeys.map((sec) => {
              const open = openMap[sec];
              const secData = docsStructure[sec];
              return (
                <Box key={sec}>
                  <ListItemButton onClick={toggleSection(sec)} sx={{ pl: 1 }}>
                    <ListItemIcon sx={{ minWidth: 24, ml: -3, mr: 0.5 }}>
                      {open ? <ExpandLess fontSize="small" /> : <ExpandMore fontSize="small" />}
                    </ListItemIcon>
                    <ListItemText primary={secData.title} primaryTypographyProps={{ fontWeight: 600 }} />
                  </ListItemButton>
                  <Collapse in={open} timeout="auto" unmountOnExit>
                    <List component="div" disablePadding sx={{ ml: 1.5, borderLeft: 1, borderColor: "divider" }}>
                      {Object.entries(secData.pages).map(([pgKey, pgVal]) => (
                        <ListItemButton
                          key={pgKey}
                          component={RouterLink}
                          to={`/docs/${version}/${sec}/${pgKey}`}
                          selected={sec === section && pgKey === page}
                        >
                          <ListItemText
                            primary={pgVal.title}
                            primaryTypographyProps={{ fontWeight: 500, fontSize: "0.875rem" }}
                          />
                        </ListItemButton>
                      ))}
                    </List>
                  </Collapse>
                </Box>
              );
            })}
          </List>
        </Drawer>
      </Hidden>

      {/* ---------------- Main content ---------------- */}
      <Box component="main" sx={{ flexGrow: 1, p: { xs: 2, md: 4 }, maxWidth: 860, mx: "auto" }}>
        <Toolbar />
        <MuiMarkdown overrides={overrides}>{mdSource}</MuiMarkdown>
        <Footer />
      </Box>
    </Box>
  );
}
