import React, { useMemo } from "react";
import { Link } from "react-router-dom";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Badge } from "@/components/ui/badge";
import { ExternalLink, MapPin } from "lucide-react";
import type { ProjectProgressItem } from "@/types/analytics";

interface LivingEarthMapProps {
  projects: ProjectProgressItem[];
  height?: string | number;
  className?: string;
  selectedProjectId?: string;
  onSelectProject?: (project: ProjectProgressItem) => void;
  showGeoJSON?: boolean;
}

// Function to create customized SVG pin markers styled with VANA design tokens
function createProjectIcon(status: string, isSelected: boolean = false): L.DivIcon {
  let bgColor = "#183D32"; // Forest Green default
  let ringColor = "#D6A76A"; // Gold ring

  if (status === "COMPLETED") {
    bgColor = "#2E7D32";
  } else if (status === "DRAFT") {
    bgColor = "#D6A76A";
    ringColor = "#183D32";
  } else if (status === "PAUSED") {
    bgColor = "#78909C";
  }

  const size = isSelected ? 36 : 28;
  const strokeWidth = isSelected ? 3 : 2;

  const html = `
    <div style="
      width: ${size}px;
      height: ${size}px;
      background-color: ${bgColor};
      border: ${strokeWidth}px solid ${ringColor};
      border-radius: 50% 50% 50% 0;
      transform: rotate(-45deg);
      box-shadow: 0 4px 8px rgba(0,0,0,0.25);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: transform 0.2s ease;
    ">
      <div style="
        width: 8px;
        height: 8px;
        background-color: #FFFFFF;
        border-radius: 50%;
        transform: rotate(45deg);
      "></div>
    </div>
  `;

  return L.divIcon({
    html,
    className: "custom-leaflet-marker",
    iconSize: [size, size],
    iconAnchor: [size / 2, size],
    popupAnchor: [0, -size],
  });
}

export const LivingEarthMap: React.FC<LivingEarthMapProps> = ({
  projects,
  height = "420px",
  className,
  selectedProjectId,
  onSelectProject,
}) => {
  // Filter projects with valid non-zero finite coordinates
  const mappedProjects = useMemo(() => {
    return projects.filter(
      (p) =>
        p.latitude !== null &&
        p.longitude !== null &&
        Number.isFinite(p.latitude) &&
        Number.isFinite(p.longitude) &&
        !(p.latitude === 0.0 && p.longitude === 0.0)
    );
  }, [projects]);

  const missingCoordsCount = projects.length - mappedProjects.length;

  // Compute center coordinates (default to India geographic center [20.5937, 78.9629] if no coords)
  const centerPosition: [number, number] = useMemo(() => {
    if (mappedProjects.length === 0) {
      return [20.5937, 78.9629];
    }
    const avgLat =
      mappedProjects.reduce((sum, p) => sum + (p.latitude || 0), 0) /
      mappedProjects.length;
    const avgLng =
      mappedProjects.reduce((sum, p) => sum + (p.longitude || 0), 0) /
      mappedProjects.length;
    return [avgLat, avgLng];
  }, [mappedProjects]);

  return (
    <div className={`relative overflow-hidden rounded-xl border border-forest/15 ${className || ""}`}>
      {mappedProjects.length === 0 ? (
        <div
          style={{ height }}
          className="flex flex-col items-center justify-center p-6 bg-forest/5 text-center"
        >
          <div className="w-12 h-12 rounded-full bg-forest/10 text-forest flex items-center justify-center mb-3">
            <MapPin className="w-6 h-6" />
          </div>
          <p className="font-manrope text-base font-bold text-forest">
            No Geographic Coordinates Available
          </p>
          <p className="text-xs text-charcoal/70 mt-1 max-w-sm">
            Projects configured with valid latitude and longitude coordinates will render interactively across the Living Earth map canvas.
          </p>
        </div>
      ) : (
        <>
          <div style={{ height, width: "100%" }}>
            <MapContainer
              center={centerPosition}
              zoom={mappedProjects.length === 1 ? 9 : 5}
              style={{ height: "100%", width: "100%" }}
              scrollWheelZoom={false}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />

              {mappedProjects.map((p) => {
                const isSelected = p.id === selectedProjectId;
                const icon = createProjectIcon(p.status, isSelected);

                return (
                  <Marker
                    key={p.id}
                    position={[p.latitude as number, p.longitude as number]}
                    icon={icon}
                    eventHandlers={{
                      click: () => onSelectProject?.(p),
                    }}
                  >
                    <Popup className="vana-map-popup">
                      <div className="p-1 min-w-[200px] space-y-2 text-charcoal">
                        <div className="flex items-start justify-between gap-2 border-b border-forest/10 pb-1.5">
                          <div>
                            <h4 className="font-manrope font-bold text-sm text-forest leading-tight">
                              {p.name}
                            </h4>
                            <span className="font-mono text-[10px] text-charcoal/60">
                              {p.code}
                            </span>
                          </div>
                          <Badge
                            variant="outline"
                            className="text-[10px] uppercase font-semibold h-4 px-1.5"
                          >
                            {p.status}
                          </Badge>
                        </div>

                        {p.targets.length > 0 ? (
                          <div className="space-y-1.5 text-xs">
                            <p className="text-[10px] uppercase tracking-wider font-semibold text-charcoal/60">
                              Verified Progress
                            </p>
                            {p.targets.map((t) => (
                              <div key={t.target_id} className="space-y-0.5">
                                <div className="flex justify-between text-[11px]">
                                  <span className="truncate max-w-[120px]">{t.metric_name}</span>
                                  <span className="font-semibold text-forest">
                                    {t.achievement_percentage}%
                                  </span>
                                </div>
                                <div className="h-1.5 w-full bg-forest/10 rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-forest rounded-full"
                                    style={{
                                      width: `${Math.min(100, Math.max(0, t.achievement_percentage))}%`,
                                    }}
                                  />
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="text-xs text-charcoal/60 italic">
                            No targets configured yet.
                          </p>
                        )}

                        <div className="pt-2 border-t border-forest/10 flex justify-end">
                          <Link
                            to={`/projects/${p.id}`}
                            className="text-xs font-semibold text-forest hover:underline flex items-center gap-1"
                          >
                            Open Workspace <ExternalLink className="w-3 h-3" />
                          </Link>
                        </div>
                      </div>
                    </Popup>
                  </Marker>
                );
              })}
            </MapContainer>
          </div>

          {missingCoordsCount > 0 && (
            <div className="absolute bottom-2 left-2 z-[1000] bg-white/95 backdrop-blur-xs px-2.5 py-1 rounded-md border border-forest/15 shadow-xs text-[11px] text-charcoal/70">
              <span className="font-semibold text-forest">{missingCoordsCount}</span> {missingCoordsCount === 1 ? "project lacks" : "projects lack"} coordinates
            </div>
          )}
        </>
      )}
    </div>
  );
};
