import React from "react";
import { Download, MapPin, FileText, Image as ImageIcon } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import type { InspectionEvidence } from "@/types/monitoring";

interface EvidenceLightboxModalProps {
  evidence: InspectionEvidence | null;
  isOpen: boolean;
  onClose: () => void;
}

export const EvidenceLightboxModal: React.FC<EvidenceLightboxModalProps> = ({
  evidence,
  isOpen,
  onClose,
}) => {
  if (!evidence) return null;

  const isImage = evidence.mime_type.startsWith("image/");
  const formattedSize =
    evidence.file_size_bytes < 1024 * 1024
      ? `${(evidence.file_size_bytes / 1024).toFixed(1)} KB`
      : `${(evidence.file_size_bytes / (1024 * 1024)).toFixed(2)} MB`;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl bg-white p-6 rounded-xl border border-vana-forest/15 shadow-xl">
        <DialogHeader className="border-b border-vana-forest/10 pb-3">
          <div className="flex items-center gap-2">
            {isImage ? (
              <ImageIcon className="h-5 w-5 text-vana-forest" />
            ) : (
              <FileText className="h-5 w-5 text-vana-forest" />
            )}
            <DialogTitle className="text-lg font-bold font-manrope text-vana-forest truncate">
              {evidence.original_filename}
            </DialogTitle>
          </div>
          <DialogDescription className="text-xs text-vana-charcoal/70">
            Uploaded on {new Date(evidence.uploaded_at).toLocaleString()} • {formattedSize}
          </DialogDescription>
        </DialogHeader>

        {/* Media Preview */}
        <div className="my-4 flex items-center justify-center bg-vana-forest/5 rounded-lg border border-vana-forest/10 overflow-hidden min-h-[240px] max-h-[420px]">
          {isImage ? (
            <img
              src={evidence.download_url}
              alt={evidence.caption || evidence.original_filename}
              className="max-h-[400px] w-auto object-contain rounded-md"
              onError={(e) => {
                // Fallback placeholder if image load fails
                (e.target as HTMLElement).style.display = "none";
              }}
            />
          ) : (
            <div className="flex flex-col items-center justify-center p-8 text-center text-vana-charcoal/70">
              <FileText className="h-16 w-16 text-vana-sage mb-2" />
              <p className="text-sm font-semibold">{evidence.original_filename}</p>
              <p className="text-xs text-vana-charcoal/50 mt-1">{evidence.mime_type}</p>
            </div>
          )}
        </div>

        {/* Caption & Metadata */}
        <div className="space-y-3 bg-vana-ivory/50 p-4 rounded-lg border border-vana-forest/10 text-xs">
          {evidence.caption && (
            <div>
              <span className="font-semibold text-vana-forest uppercase tracking-wider text-[10px] block">
                Caption
              </span>
              <p className="text-vana-charcoal text-sm mt-0.5">{evidence.caption}</p>
            </div>
          )}

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-1 border-t border-vana-forest/10">
            <div>
              <span className="text-[10px] text-vana-charcoal/60 uppercase font-semibold block">
                Format
              </span>
              <span className="font-medium text-vana-charcoal">{evidence.mime_type}</span>
            </div>
            <div>
              <span className="text-[10px] text-vana-charcoal/60 uppercase font-semibold block">
                File Size
              </span>
              <span className="font-medium text-vana-charcoal">{formattedSize}</span>
            </div>
            {evidence.latitude !== null &&
              evidence.latitude !== undefined &&
              evidence.longitude !== null &&
              evidence.longitude !== undefined && (
                <div>
                  <span className="text-[10px] text-vana-charcoal/60 uppercase font-semibold block flex items-center gap-1">
                    <MapPin className="h-3 w-3 text-vana-gold" /> GPS Coordinates
                  </span>
                  <span className="font-medium text-vana-charcoal">
                    {Number(evidence.latitude).toFixed(5)}, {Number(evidence.longitude).toFixed(5)}
                  </span>
                </div>
              )}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="outline" size="sm" onClick={onClose}>
            Close
          </Button>
          <Button
            size="sm"
            className="bg-vana-forest text-white gap-1.5"
            onClick={() => window.open(evidence.download_url, "_blank")}
          >
            <Download className="h-4 w-4" /> Download Original
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
