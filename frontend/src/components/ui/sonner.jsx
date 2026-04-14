import { Toaster as Sonner, toast } from "sonner"

const Toaster = ({
  ...props
}) => {
  return (
    <Sonner
      theme="dark"
      className="toaster group"
      toastOptions={{
        classNames: {
          toast:
            "group toast group-[.toaster]:bg-[#0A0A12] group-[.toaster]:text-[#F2F2F5] group-[.toaster]:border-[#8B9DB5]/20 group-[.toaster]:shadow-lg",
          description: "group-[.toast]:text-[#A0A0B0]",
          actionButton:
            "group-[.toast]:bg-[#8B9DB5] group-[.toast]:text-[#030305]",
          cancelButton:
            "group-[.toast]:bg-[#12121C] group-[.toast]:text-[#A0A0B0]",
        },
      }}
      {...props} />
  );
}

export { Toaster, toast }
