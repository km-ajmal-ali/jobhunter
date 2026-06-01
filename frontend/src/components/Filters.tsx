import { SourceInfo, CountryInfo } from "../types";
import SourceSelect from "./SourceSelect";
import CountrySelect from "./CountrySelect";

interface FiltersProps {
  sources: SourceInfo[];
  countries: CountryInfo[];
  selectedSource: string;
  selectedCountry: string;
  onFilterChange: (filters: { source?: string; country?: string }) => void;
}

export default function Filters({
  sources,
  countries,
  selectedSource,
  selectedCountry,
  onFilterChange,
}: FiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <SourceSelect
        sources={sources}
        value={selectedSource}
        onChange={(name) => onFilterChange({ source: name })}
      />

      <CountrySelect
        countries={countries}
        value={selectedCountry}
        onChange={(code) => onFilterChange({ country: code })}
      />
    </div>
  );
}
