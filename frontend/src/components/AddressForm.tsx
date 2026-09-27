import { FormEvent, useState } from "react";

interface Props {
  onSubmit: (address: string) => void;
  disabled: boolean;
}

export default function AddressForm({ onSubmit, disabled }: Props) {
  const [address, setAddress] = useState("");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (address.trim()) onSubmit(address.trim());
  }

  return (
    <form className="address-form" onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="301 Congress Ave, Austin, TX"
        value={address}
        onChange={(e) => setAddress(e.target.value)}
        disabled={disabled}
      />
      <button type="submit" disabled={disabled || !address.trim()}>
        {disabled ? "Generating…" : "Get report"}
      </button>
    </form>
  );
}
