// @mui
import CardMedia from '@mui/material/CardMedia';
import Chip from '@mui/material/Chip';
import Typography from '@mui/material/Typography';

// @project
import Hero17 from './Hero17';

/***************************  HERO 17 - DATA  ***************************/

const data = {
  chip: {
    label: (
      <>
        <Typography variant="caption" sx={{ color: 'text.secondary' }}>
          From PDF
        </Typography>
        <Chip
          label={
            <Typography variant="caption" sx={{ color: 'primary.main' }}>
              to Structured Knowledge
            </Typography>
          }
          sx={{ height: 24, bgcolor: 'primary.lighter', mr: -1, ml: 0.75, '& .MuiChip-label': { px: 1.25 } }}
          icon={
            <CardMedia
              component="img"
              image="https://www.jaist.ac.jp/is/labs/nguyen-lab/systems/docora/assets/images/shared/celebration.svg"
              sx={{ width: 16, height: 16 }}
              alt="celebration"
              loading="lazy"
            />
          }
        />
      </>
    )
  },
  headLine: 'Docora: Extract & Visualize Knowledge from PDFs',
  captionLine: 'Domain-agnostic IE with configurable schemas and plug-in NER/RE backends. Annotate in context, verify suggestions, and export structured data — all inside the PDF.',
  primaryBtn: { children: 'Explore Docora' },
  // videoSrc: 'https://d2elhhoq00m1pj.cloudfront.net/saasable-intro.mp4',
  videoSrc: 'https://www.jaist.ac.jp/is/labs/nguyen-lab/systems/polyminder/assets/2024-09-25%2015-21-03.mp4',
  videoThumbnail: 'https://www.jaist.ac.jp/is/labs/nguyen-lab/systems/docora/assets/videos/thumbnails/intro-thumbnail.png',
  listData: [
    { image: 'https://www.jaist.ac.jp/is/labs/nguyen-lab/systems/docora/assets/images/shared/react.svg', title: 'React 18' },
    { image: 'https://www.jaist.ac.jp/is/labs/nguyen-lab/systems/docora/assets/images/shared/Vite.js.svg', title: 'Vite.js' },
    { image: 'https://www.jaist.ac.jp/is/labs/nguyen-lab/systems/docora/assets/images/shared/material-ui.svg', title: 'Material UI v7' },
    { image: 'https://www.jaist.ac.jp/is/labs/nguyen-lab/systems/docora/assets/images/shared/typescript.svg', title: 'TypeScript' },
    { image: 'https://www.jaist.ac.jp/is/labs/nguyen-lab/systems/docora/assets/images/shared/javascript.svg', title: 'FastAPI' },
    { image: 'https://www.jaist.ac.jp/is/labs/nguyen-lab/systems/docora/assets/images/shared/pymupdf.svg', title: 'PyMuPDF' },
    { image: 'https://www.jaist.ac.jp/is/labs/nguyen-lab/systems/docora/assets/images/shared/PostgresSQL.svg', title: 'PostgreSQL' }
  ]
};

/***************************  BLOCK - HERO 17  ***************************/

export default function BlockHero17() {
  return <Hero17 {...data} />;
}