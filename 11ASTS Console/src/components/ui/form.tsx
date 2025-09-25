"use client"

import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import {
  Controller,
  type ControllerProps,
  type FieldPath,
  type FieldValues,
  FormProvider,
  useFormContext,
} from "react-hook-form"

import { cn } from "@/lib/utils"
import { Label } from "@/components/ui/label"

// Re-export Provider as Form for ergonomic API
// Usage: <Form {...form}><form>...</form></Form>
export const Form = FormProvider

// Provide field name to descendants (Label/Message) for a11y and errors
const FormFieldContext = React.createContext<{ name: string } | undefined>(
  undefined
)

export const FormField = <
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>,
  TTransformedValues extends FieldValues = TFieldValues
>(
  props: ControllerProps<TFieldValues, TName, TTransformedValues>
) => {
  return (
    <FormFieldContext.Provider value={{ name: props.name as string }}>
      <Controller {...props} />
    </FormFieldContext.Provider>
  )
}

export const useFormField = () => {
  const fieldContext = React.useContext(FormFieldContext)
  const form = useFormContext()
  const fieldState = fieldContext?.name
    ? form.getFieldState(fieldContext.name)
    : undefined

  return {
    name: fieldContext?.name,
    formItemId: fieldContext?.name ? `${fieldContext.name}-form-item` : undefined,
    formDescriptionId: fieldContext?.name
      ? `${fieldContext.name}-form-item-description`
      : undefined,
    formMessageId: fieldContext?.name
      ? `${fieldContext.name}-form-item-message`
      : undefined,
    error: fieldState?.error,
  }
}

const FormItemContext = React.createContext<{ id: string } | undefined>(
  undefined
)

export const FormItem = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => {
    const id = React.useId()
    return (
      <FormItemContext.Provider value={{ id }}>
        <div ref={ref} className={cn("space-y-2", className)} {...props} />
      </FormItemContext.Provider>
    )
  }
)
FormItem.displayName = "FormItem"

export const FormLabel = React.forwardRef<
  React.ElementRef<typeof Label>,
  React.ComponentPropsWithoutRef<typeof Label>
>(({ className, ...props }, ref) => {
  const itemContext = React.useContext(FormItemContext)
  const { formItemId } = useFormField()

  return (
    <Label
      ref={ref}
      className={cn(className)}
      htmlFor={itemContext?.id ?? formItemId}
      {...props}
    />
  )
})
FormLabel.displayName = "FormLabel"

export const FormControl = React.forwardRef<
  React.ElementRef<typeof Slot>,
  React.ComponentPropsWithoutRef<typeof Slot>
>(({ className, ...props }, ref) => {
  const itemContext = React.useContext(FormItemContext)
  const { formDescriptionId, formMessageId } = useFormField()

  return (
    <Slot
      ref={ref}
      className={className}
      id={itemContext?.id}
      aria-describedby={
        [formDescriptionId, formMessageId].filter(Boolean).join(" ") || undefined
      }
      aria-invalid={!!formMessageId}
      {...props}
    />
  )
})
FormControl.displayName = "FormControl"

export const FormDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => {
  const { formDescriptionId } = useFormField()
  return (
    <p
      ref={ref}
      id={formDescriptionId}
      className={cn("text-sm text-muted-foreground", className)}
      {...props}
    />
  )
})
FormDescription.displayName = "FormDescription"

export const FormMessage = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, children, ...props }, ref) => {
  const { error, formMessageId } = useFormField()
  const body = error ? String(error.message) : children

  if (!body) return null

  return (
    <p
      ref={ref}
      id={formMessageId}
      className={cn("text-sm font-medium text-destructive", className)}
      {...props}
    >
      {body}
    </p>
  )
})
FormMessage.displayName = "FormMessage"