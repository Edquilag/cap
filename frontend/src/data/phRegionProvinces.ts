export type RegionProvinceMap = {
  regionName: string;
  displayName: string;
  sourceCode: string;
  provinces: string[];
};

// Source: https://psgc.gitlab.io/api/regions/ and https://psgc.gitlab.io/api/provinces/
// Synced: 2026-02-15
export const PH_REGION_PROVINCES: RegionProvinceMap[] = [
  {
    regionName: "Bangsamoro Autonomous Region in Muslim Mindanao",
    displayName: "BARMM",
    sourceCode: "150000000",
    provinces: [
      "Basilan",
      "Lanao Del Sur",
      "Maguindanao",
      "Sulu",
      "Tawi-Tawi",
    ],
  },
  {
    regionName: "Cordillera Administrative Region",
    displayName: "CAR",
    sourceCode: "140000000",
    provinces: [
      "Abra",
      "Apayao",
      "Benguet",
      "Ifugao",
      "Kalinga",
      "Mountain Province",
    ],
  },
  {
    regionName: "MIMAROPA Region",
    displayName: "MIMAROPA Region",
    sourceCode: "170000000",
    provinces: [
      "Marinduque",
      "Occidental Mindoro",
      "Oriental Mindoro",
      "Palawan",
      "Romblon",
    ],
  },
  {
    regionName: "National Capital Region",
    displayName: "NCR",
    sourceCode: "130000000",
    provinces: [
    ],
  },
  {
    regionName: "Region I",
    displayName: "Ilocos Region",
    sourceCode: "010000000",
    provinces: [
      "Ilocos Norte",
      "Ilocos Sur",
      "La Union",
      "Pangasinan",
    ],
  },
  {
    regionName: "Region II",
    displayName: "Cagayan Valley",
    sourceCode: "020000000",
    provinces: [
      "Batanes",
      "Cagayan",
      "Isabela",
      "Nueva Vizcaya",
      "Quirino",
    ],
  },
  {
    regionName: "Region III",
    displayName: "Central Luzon",
    sourceCode: "030000000",
    provinces: [
      "Aurora",
      "Bataan",
      "Bulacan",
      "Nueva Ecija",
      "Pampanga",
      "Tarlac",
      "Zambales",
    ],
  },
  {
    regionName: "Region IV-A",
    displayName: "CALABARZON",
    sourceCode: "040000000",
    provinces: [
      "Batangas",
      "Cavite",
      "Laguna",
      "Quezon",
      "Rizal",
    ],
  },
  {
    regionName: "Region IX",
    displayName: "Zamboanga Peninsula",
    sourceCode: "090000000",
    provinces: [
      "Zamboanga Del Norte",
      "Zamboanga Del Sur",
      "Zamboanga Sibugay",
    ],
  },
  {
    regionName: "Region V",
    displayName: "Bicol Region",
    sourceCode: "050000000",
    provinces: [
      "Albay",
      "Camarines Norte",
      "Camarines Sur",
      "Catanduanes",
      "Masbate",
      "Sorsogon",
    ],
  },
  {
    regionName: "Region VI",
    displayName: "Western Visayas",
    sourceCode: "060000000",
    provinces: [
      "Aklan",
      "Antique",
      "Capiz",
      "Guimaras",
      "Iloilo",
      "Negros Occidental",
    ],
  },
  {
    regionName: "Region VII",
    displayName: "Central Visayas",
    sourceCode: "070000000",
    provinces: [
      "Bohol",
      "Cebu",
      "Negros Oriental",
      "Siquijor",
    ],
  },
  {
    regionName: "Region VIII",
    displayName: "Eastern Visayas",
    sourceCode: "080000000",
    provinces: [
      "Biliran",
      "Eastern Samar",
      "Leyte",
      "Northern Samar",
      "Samar",
      "Southern Leyte",
    ],
  },
  {
    regionName: "Region X",
    displayName: "Northern Mindanao",
    sourceCode: "100000000",
    provinces: [
      "Bukidnon",
      "Camiguin",
      "Lanao Del Norte",
      "Misamis Occidental",
      "Misamis Oriental",
    ],
  },
  {
    regionName: "Region XI",
    displayName: "Davao Region",
    sourceCode: "110000000",
    provinces: [
      "Davao De Oro",
      "Davao Del Norte",
      "Davao Del Sur",
      "Davao Occidental",
      "Davao Oriental",
    ],
  },
  {
    regionName: "Region XII",
    displayName: "SOCCSKSARGEN",
    sourceCode: "120000000",
    provinces: [
      "Cotabato",
      "Sarangani",
      "South Cotabato",
      "Sultan Kudarat",
    ],
  },
  {
    regionName: "Region XIII",
    displayName: "Caraga",
    sourceCode: "160000000",
    provinces: [
      "Agusan Del Norte",
      "Agusan Del Sur",
      "Dinagat Islands",
      "Surigao Del Norte",
      "Surigao Del Sur",
    ],
  },
];
