// frontend/src/pages/CreateLibrarianPage.tsx
// UI-SPEC Screen 4: Create Librarian (/admin/users/new) — AUTH-06
// Access: admin_librarian only (ProtectedRoute guards this route — CM-7 note: UX only, backend enforces)
// Copywriting Contract: exact match per UI-SPEC

import { Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { api } from "@/lib/axios";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";

const createLibrarianSchema = z.object({
  full_name: z
    .string()
    .min(2, "Full name must be at least 2 characters")
    .max(100, "Full name must be at most 100 characters"),
  email: z.string().email("Please enter a valid email address"),
  password: z.string().min(8, "Minimum 8 characters"),
});

type CreateLibrarianFormValues = z.infer<typeof createLibrarianSchema>;

interface ApiError {
  response?: { status?: number };
}

export function CreateLibrarianPage() {
  const form = useForm<CreateLibrarianFormValues>({
    resolver: zodResolver(createLibrarianSchema),
    mode: "onTouched",
    reValidateMode: "onChange",
    defaultValues: {
      full_name: "",
      email: "",
      password: "",
    },
  });

  const mutation = useMutation({
    mutationFn: (values: CreateLibrarianFormValues) =>
      api.post("/admin/users", values),
    onSuccess: () => {
      // Sonner toast per UI-SPEC Screen 4 success state — exact copy
      toast.success("Librarian account created.");
      // Reset form so admin can create another account without leaving the page
      form.reset();
    },
    onError: (err: ApiError) => {
      // Error messages displayed via Alert below the form fields
      // Handled in JSX via mutation.error — no action needed here
      void err;
    },
  });

  const onSubmit = (values: CreateLibrarianFormValues) => {
    mutation.reset(); // clear previous error before new attempt
    mutation.mutate(values);
  };

  // Determine error message from API response status
  const apiError = mutation.error as ApiError | null;
  const errorMessage = apiError
    ? apiError.response?.status === 409
      ? "An account with this email already exists."
      : apiError.response?.status === 403
        ? "You don't have permission to perform this action."
        : "Unable to connect. Check your internet connection and try again."
    : null;

  const isSubmitting = mutation.isPending;

  return (
    <div className="flex items-center justify-center px-4 py-16">
      <Card className="w-full max-w-[400px] shadow-md">
        <CardHeader className="pb-4">
          <CardTitle className="text-xl font-semibold">
            Create librarian account
          </CardTitle>
          <CardDescription>
            The new librarian will be able to log in immediately.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Form {...form}>
            <form
              onSubmit={form.handleSubmit(onSubmit)}
              className="space-y-4"
              noValidate
            >
              <FormField
                control={form.control}
                name="full_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel htmlFor="librarian-full-name">Full name</FormLabel>
                    <FormControl>
                      <Input
                        id="librarian-full-name"
                        type="text"
                        autoComplete="name"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel htmlFor="librarian-email">Email</FormLabel>
                    <FormControl>
                      <Input
                        id="librarian-email"
                        type="email"
                        autoComplete="off"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel htmlFor="librarian-password">
                      Temporary password
                    </FormLabel>
                    <FormControl>
                      <Input
                        id="librarian-password"
                        type="password"
                        autoComplete="new-password"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {errorMessage && (
                <Alert variant="destructive" role="alert">
                  <AlertDescription>{errorMessage}</AlertDescription>
                </Alert>
              )}

              <Button
                type="submit"
                className="w-full h-11"
                disabled={isSubmitting}
                aria-busy={isSubmitting}
                aria-disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <>
                    <Loader2
                      className="mr-2 h-4 w-4 animate-spin"
                      aria-hidden="true"
                    />
                    Creating account...
                  </>
                ) : (
                  "Create account"
                )}
              </Button>
            </form>
          </Form>

          {/* Back to dashboard link — UI-SPEC Screen 4 cancel link */}
          <p className="text-sm">
            <Link to="/dashboard" className="text-primary hover:underline">
              ← Back to dashboard
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
